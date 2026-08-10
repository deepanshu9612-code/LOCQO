"""LOCQO admin operations — campus data, accounts, announcements, analytics.

This module is the trust boundary between an admin's browser and the graph the router
walks: everything validates before it writes. A bad row here becomes a 500 on every
route lookup for every user, so nothing is taken on faith.

Each function owns its transaction and commits; callers just map ValueError -> HTTP 400.
"""
import json
import math
import re
from datetime import datetime, timezone

import auth
from seed_db import dist  # the seed's distance formula — reused, not re-derived

TYPES = {"gate", "block", "lab", "eatery", "ground", "hostel", "parking",
         "amenity", "utility", "corridor", "junction", "library", "stairs"}
EDGE_KINDS = {"walk", "door", "stairs", "lift"}

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}$")
TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]([01]\d|2[0-3]):[0-5]\d$")
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
ROOM_TYPES = ("lab", "library")   # what counts as a bookable teaching space

# Dialled by a person, not by the app. 112/101/102 are India's national emergency
# numbers. CAMPUS_SECURITY is intentionally blank — put the real KRMU number here;
# the UI says it is unset rather than showing an invented one.
CAMPUS_SECURITY = ""
EMERGENCY_CONTACTS = [
    {"label": "Campus Security", "number": CAMPUS_SECURITY},
    {"label": "Emergency (all services)", "number": "112"},
    {"label": "Ambulance", "number": "102"},
    {"label": "Fire", "number": "101"},
]
LEVEL_RE = re.compile(r"^([A-D])-(\d)$")
SCENE_RE = re.compile(r"^\d{1,6}$")
COORD_MAX = 200.0


def _now():
    return datetime.now(timezone.utc).isoformat()


def _num(value, label, lo, hi):
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.")
    if not math.isfinite(n) or not (lo <= n <= hi):
        raise ValueError(f"{label} must be between {lo} and {hi}.")
    return n


# ---- locations -----------------------------------------------------------
def _clean_location(d):
    """Validate a location payload into the exact row we're willing to store."""
    lid = (d.get("id") or "").strip().lower()
    if not ID_RE.match(lid):
        raise ValueError("Id must be lowercase letters, digits and hyphens, "
                         "2–49 characters — e.g. new-lab-1.")
    name = (d.get("name") or "").strip()
    if not 1 <= len(name) <= 80:
        raise ValueError("Name is required and must be 80 characters or fewer.")
    typ = (d.get("type") or "").strip().lower()
    if typ not in TYPES:
        raise ValueError(f"Type must be one of: {', '.join(sorted(TYPES))}.")

    level = (d.get("level") or "outdoor").strip()
    # block and floor are DERIVED from an indoor level, so they can never disagree with it
    m = LEVEL_RE.match(level)
    if m:
        block, floor = m.group(1), int(m.group(2))
    elif level == "outdoor":
        block = (d.get("block") or "").strip().upper() or None
        if typ != "block":
            block = None  # only a building carries a letter outdoors
        if block and block not in {"A", "B", "C", "D"}:
            raise ValueError("Block must be A, B, C or D.")
        floor = None
    else:
        raise ValueError("Level must be 'outdoor' or a floor like B-2.")

    room = (d.get("room") or "").strip() or None
    if room and len(room) > 20:
        raise ValueError("Room code is too long.")

    scene = (d.get("tour_scene") or "").strip() or None
    if scene and not SCENE_RE.match(scene):
        raise ValueError("Tour scene must be a short number, e.g. 9937.")

    raw_aliases = d.get("aliases") or []
    if isinstance(raw_aliases, str):
        raw_aliases = [a.strip() for a in raw_aliases.split(",")]
    aliases = [a.strip().lower() for a in raw_aliases if isinstance(a, str) and a.strip()]
    if len(aliases) > 10 or any(len(a) > 40 for a in aliases):
        raise ValueError("Up to 10 aliases, each 40 characters or fewer.")

    return dict(id=lid, name=name, type=typ, level=level, block=block, floor=floor,
                room=room, x=_num(d.get("x"), "X", 0, COORD_MAX),
                y=_num(d.get("y"), "Y", 0, COORD_MAX),
                aliases=json.dumps(aliases), tour_scene=scene)


def list_locations(con):
    return [dict(r) for r in con.execute(
        "SELECT * FROM locations ORDER BY level, type, name")]


def create_location(con, d):
    row = _clean_location(d)
    if con.execute("SELECT 1 FROM locations WHERE id=?", (row["id"],)).fetchone():
        raise ValueError(f"A location with id '{row['id']}' already exists.")
    con.execute(
        "INSERT INTO locations (id,name,type,level,block,floor,room,x,y,aliases,tour_scene)"
        " VALUES (:id,:name,:type,:level,:block,:floor,:room,:x,:y,:aliases,:tour_scene)", row)
    con.commit()
    return row


def update_location(con, d):
    row = _clean_location(d)
    if not con.execute("SELECT 1 FROM locations WHERE id=?", (row["id"],)).fetchone():
        raise ValueError("No such location.")
    con.execute(
        "UPDATE locations SET name=:name, type=:type, level=:level, block=:block,"
        " floor=:floor, room=:room, x=:x, y=:y, aliases=:aliases, tour_scene=:tour_scene"
        " WHERE id=:id", row)
    con.commit()
    return row


def delete_location(con, lid):
    """Delete a location AND its paths in one transaction.

    Leaving a dangling edge would KeyError in routing.load_graph and 500 every route
    lookup for every user, so the cascade is not optional.
    """
    lid = (lid or "").strip()
    if not con.execute("SELECT 1 FROM locations WHERE id=?", (lid,)).fetchone():
        raise ValueError("No such location.")
    dropped = con.execute(
        "SELECT count(*) FROM edges WHERE a=? OR b=?", (lid, lid)).fetchone()[0]
    con.execute("DELETE FROM edges WHERE a=? OR b=?", (lid, lid))
    con.execute("DELETE FROM locations WHERE id=?", (lid,))
    con.commit()
    return {"deleted": lid, "paths_removed": dropped}


# ---- paths (edges) -------------------------------------------------------
def list_edges(con):
    return [dict(r) for r in con.execute(
        "SELECT e.rowid AS rowid, e.a, e.b, e.weight, e.kind,"
        " la.name AS a_name, lb.name AS b_name FROM edges e"
        " JOIN locations la ON la.id = e.a JOIN locations lb ON lb.id = e.b"
        " ORDER BY la.name, lb.name")]


def suggest_weight(con, a, b):
    """Outdoor pairs get the real distance; anything else gets a sane indoor default."""
    ra = con.execute("SELECT x,y,level FROM locations WHERE id=?", (a,)).fetchone()
    rb = con.execute("SELECT x,y,level FROM locations WHERE id=?", (b,)).fetchone()
    if not ra or not rb:
        return None
    if ra["level"] == "outdoor" and rb["level"] == "outdoor":
        return float(dist((ra["x"], ra["y"]), (rb["x"], rb["y"])))
    return 4.0


def create_edge(con, d):
    a, b = (d.get("a") or "").strip(), (d.get("b") or "").strip()
    if not a or not b:
        raise ValueError("Pick both ends of the path.")
    if a == b:
        raise ValueError("A path has to join two different places.")
    for nid in (a, b):
        if not con.execute("SELECT 1 FROM locations WHERE id=?", (nid,)).fetchone():
            raise ValueError(f"No location with id '{nid}'.")
    kind = (d.get("kind") or "walk").strip().lower()
    if kind not in EDGE_KINDS:
        raise ValueError(f"Path type must be one of: {', '.join(sorted(EDGE_KINDS))}.")
    weight = d.get("weight")
    weight = suggest_weight(con, a, b) if weight in (None, "") else _num(weight, "Weight", 0.1, 1000)
    # same check-then-insert race as create_slot — there is no unique constraint that can
    # express "unordered pair", so the write lock is what keeps duplicates out
    con.execute("BEGIN IMMEDIATE")
    try:
        if con.execute("SELECT 1 FROM edges WHERE (a=? AND b=?) OR (a=? AND b=?)",
                       (a, b, b, a)).fetchone():
            raise ValueError("A path already connects those two places.")
        con.execute("INSERT INTO edges (a,b,weight,kind) VALUES (?,?,?,?)",
                    (a, b, weight, kind))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {"a": a, "b": b, "weight": weight, "kind": kind}


def delete_edge(con, a, b):
    cur = con.execute("DELETE FROM edges WHERE (a=? AND b=?) OR (a=? AND b=?)", (a, b, b, a))
    con.commit()
    if not cur.rowcount:
        raise ValueError("No such path.")
    return {"removed": cur.rowcount}


# ---- users ---------------------------------------------------------------
def list_users(con):
    return [{"id": r["id"], "username": r["username"], "name": r["name"],
             "role": r["role"], "active": r["active"], "created_at": r["created_at"]}
            for r in con.execute("SELECT * FROM users ORDER BY role, username")]


def _active_admins(con):
    return con.execute(
        "SELECT count(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]


def create_user(con, d):
    """Admin-provisioned account. Role IS honoured here — the caller is a verified admin."""
    role = (d.get("role") or "student").strip()
    uid = auth.create_user(con, d.get("username"), d.get("name"), d.get("password"), role=role)
    con.commit()
    return {"id": uid}


def update_user(con, actor_id, d):
    """Change role / active / password. Cannot strand the app without an admin."""
    try:
        uid = int(d.get("id"))
    except (TypeError, ValueError):
        raise ValueError("Which user?")
    row = con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if row is None:
        raise ValueError("No such user.")

    role = (d.get("role") or row["role"]).strip()
    active = 1 if d.get("active", row["active"]) else 0
    if role not in ("student", "admin"):
        raise ValueError("Unknown role.")
    if uid == actor_id and (role != "admin" or not active):
        raise ValueError("You can't remove your own admin access.")
    was_admin = row["role"] == "admin" and row["active"]
    if was_admin and not (role == "admin" and active) and _active_admins(con) <= 1:
        raise ValueError("That's the last active admin — promote someone else first.")

    con.execute("UPDATE users SET role=?, active=? WHERE id=?", (role, active, uid))
    if not active:
        con.execute("DELETE FROM sessions WHERE user_id=?", (uid,))  # log them out now
    if d.get("password"):
        auth.set_password(con, uid, d["password"])
    con.commit()
    return {"id": uid, "role": role, "active": active}


# ---- announcements -------------------------------------------------------
def list_announcements(con, active_only=True):
    q = ("SELECT a.id, a.body, a.active, a.starts_at, a.location_id, a.created_at,"
         " l.name AS venue FROM announcements a"
         " LEFT JOIN locations l ON l.id = a.location_id")
    if active_only:
        q += " WHERE a.active=1"
    return [dict(r) for r in con.execute(q + " ORDER BY a.id DESC LIMIT 50")]


def create_announcement(con, author_id, body, starts_at=None, location_id=None):
    """No date -> a standing notice (the student banner). A date -> an upcoming event."""
    body = (body or "").strip()
    if not 1 <= len(body) <= 300:
        raise ValueError("Announcement must be 1–300 characters.")
    starts_at = (starts_at or "").strip() or None
    if starts_at and not DATETIME_RE.match(starts_at):
        raise ValueError("Date must look like 2026-08-14 17:30.")
    location_id = (location_id or "").strip() or None
    if location_id and not con.execute(
            "SELECT 1 FROM locations WHERE id=?", (location_id,)).fetchone():
        raise ValueError("That venue is not a known location.")
    cur = con.execute(
        "INSERT INTO announcements (body, author_id, starts_at, location_id, created_at)"
        " VALUES (?,?,?,?,?)", (body, author_id, starts_at, location_id, _now()))
    con.commit()
    return {"id": cur.lastrowid, "body": body, "starts_at": starts_at}


def delete_announcement(con, aid):
    cur = con.execute("DELETE FROM announcements WHERE id=?", (aid,))
    con.commit()
    if not cur.rowcount:
        raise ValueError("No such announcement.")
    return {"removed": aid}


# ---- analytics -----------------------------------------------------------
# ---- timetable & the empty-classroom finder -------------------------------
def _minutes(value, label):
    m = TIME_RE.match((value or "").strip())
    if not m:
        raise ValueError(f"{label} must look like 09:30.")
    return int(m.group(1)) * 60 + int(m.group(2))


def hhmm(mins):
    return f"{mins // 60:02d}:{mins % 60:02d}"


def list_timetable(con):
    return [dict(r, start=hhmm(r["start_min"]), end=hhmm(r["end_min"]),
                 day=WEEKDAYS[r["weekday"]])
            for r in con.execute(
                "SELECT t.*, l.name AS room FROM timetable t"
                " JOIN locations l ON l.id = t.location_id"
                " ORDER BY t.weekday, t.start_min, l.name")]


def create_slot(con, d):
    room = (d.get("location_id") or "").strip()
    if not con.execute("SELECT 1 FROM locations WHERE id=?", (room,)).fetchone():
        raise ValueError("Pick a room that exists.")
    try:
        weekday = int(d.get("weekday"))
    except (TypeError, ValueError):
        raise ValueError("Pick a day.")
    if not 0 <= weekday <= 6:
        raise ValueError("Pick a day.")
    start = _minutes(d.get("start"), "Start time")
    end = _minutes(d.get("end"), "End time")
    if end <= start:
        raise ValueError("The end time has to be after the start time.")
    title = (d.get("title") or "").strip()
    if not 1 <= len(title) <= 80:
        raise ValueError("Say what's on in the room (1–80 characters).")
    # Check-then-insert has to hold the write lock for the whole pair, or two concurrent
    # requests both see "no clash" and both land. BEGIN IMMEDIATE takes it up front.
    con.execute("BEGIN IMMEDIATE")
    try:
        clash = con.execute(
            "SELECT title, start_min, end_min FROM timetable WHERE location_id=? AND weekday=?"
            " AND start_min < ? AND end_min > ?", (room, weekday, end, start)).fetchone()
        if clash:
            raise ValueError(f"That clashes with {clash['title']} "
                             f"({hhmm(clash['start_min'])}–{hhmm(clash['end_min'])}).")
        con.execute(
            "INSERT INTO timetable (location_id,weekday,start_min,end_min,title)"
            " VALUES (?,?,?,?,?)", (room, weekday, start, end, title))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {"location_id": room, "weekday": weekday, "start": hhmm(start), "end": hhmm(end)}


def delete_slot(con, slot_id):
    cur = con.execute("DELETE FROM timetable WHERE id=?", (slot_id,))
    con.commit()
    if not cur.rowcount:
        raise ValueError("No such timetable slot.")
    return {"removed": slot_id}


def free_rooms(con, weekday, minute):
    """Every teaching space, flagged free or busy at that moment, and until when."""
    rooms = [dict(r) for r in con.execute(
        "SELECT id, name, room, block, floor FROM locations WHERE type IN (?,?)"
        " ORDER BY name", ROOM_TYPES)]
    slots = [dict(r) for r in con.execute(
        "SELECT location_id, start_min, end_min, title FROM timetable WHERE weekday=?",
        (weekday,))]
    by_room = {}
    for s in slots:
        by_room.setdefault(s["location_id"], []).append(s)

    for r in rooms:
        mine = sorted(by_room.get(r["id"], []), key=lambda s: s["start_min"])
        busy = next((s for s in mine if s["start_min"] <= minute < s["end_min"]), None)
        if busy:
            r.update(free=False, until=hhmm(busy["end_min"]), what=busy["title"])
        else:
            nxt = next((s for s in mine if s["start_min"] > minute), None)
            r.update(free=True,
                     until=hhmm(nxt["start_min"]) if nxt else None,
                     what=nxt["title"] if nxt else None)
    total = con.execute("SELECT count(*) FROM timetable").fetchone()[0]
    return {"weekday": weekday, "day": WEEKDAYS[weekday], "time": hhmm(minute),
            "rooms": rooms, "has_timetable": total > 0}


# ---- lost & found ---------------------------------------------------------
def list_lost_found(con, statuses=("approved",), user_id=None):
    """Approved items for everyone; a student additionally sees their own pending ones."""
    marks = ",".join("?" * len(statuses))
    params = list(statuses)
    where = f"lf.status IN ({marks})"
    if user_id is not None:
        where = f"({where} OR lf.user_id = ?)"
        params.append(user_id)
    return [dict(r) for r in con.execute(
        "SELECT lf.id, lf.kind, lf.title, lf.details, lf.contact, lf.status,"
        " lf.created_at, lf.user_id, l.name AS place, u.name AS posted_by"
        " FROM lost_found lf LEFT JOIN locations l ON l.id = lf.location_id"
        " LEFT JOIN users u ON u.id = lf.user_id"
        f" WHERE {where} ORDER BY lf.id DESC LIMIT 100", params)]


def create_lost_found(con, user_id, d):
    kind = (d.get("kind") or "").strip().lower()
    if kind not in ("lost", "found"):
        raise ValueError("Say whether you lost it or found it.")
    title = (d.get("title") or "").strip()
    if not 1 <= len(title) <= 80:
        raise ValueError("Give the item a short name (1–80 characters).")
    details = (d.get("details") or "").strip()[:400] or None
    contact = (d.get("contact") or "").strip()[:80] or None
    place = (d.get("location_id") or "").strip() or None
    if place and not con.execute("SELECT 1 FROM locations WHERE id=?", (place,)).fetchone():
        raise ValueError("Pick a place from the list.")
    cur = con.execute(
        "INSERT INTO lost_found (kind,title,details,location_id,contact,user_id,created_at)"
        " VALUES (?,?,?,?,?,?,?)", (kind, title, details, place, contact, user_id, _now()))
    con.commit()
    return {"id": cur.lastrowid, "status": "pending"}


def moderate_lost_found(con, item_id, status, actor_id=None, is_admin=False):
    """Admins approve/reject anything; a poster may resolve their own approved post."""
    row = con.execute("SELECT * FROM lost_found WHERE id=?", (item_id,)).fetchone()
    if row is None:
        raise ValueError("No such item.")
    if status not in ("approved", "rejected", "resolved"):
        raise ValueError("Unknown action.")
    if not is_admin and not (status == "resolved" and row["user_id"] == actor_id):
        raise ValueError("That isn't yours to change.")
    con.execute("UPDATE lost_found SET status=? WHERE id=?", (status, item_id))
    con.commit()
    return {"id": item_id, "status": status}


def delete_lost_found(con, item_id):
    cur = con.execute("DELETE FROM lost_found WHERE id=?", (item_id,))
    con.commit()
    if not cur.rowcount:
        raise ValueError("No such item.")
    return {"removed": item_id}


# ---- emergency ------------------------------------------------------------
def raise_sos(con, user_id, d):
    """Record an in-app alert. This does not contact emergency services."""
    place = (d.get("location_id") or "").strip() or None
    if place and not con.execute("SELECT 1 FROM locations WHERE id=?", (place,)).fetchone():
        raise ValueError("Pick a place from the list.")
    note = (d.get("note") or "").strip()[:200] or None
    cur = con.execute(
        "INSERT INTO sos_alerts (user_id,location_id,note,created_at) VALUES (?,?,?,?)",
        (user_id, place, note, _now()))
    con.commit()
    return {"id": cur.lastrowid, "status": "open"}


def list_sos(con):
    return [dict(r) for r in con.execute(
        "SELECT s.id, s.note, s.status, s.created_at, l.name AS place,"
        " u.name AS raised_by, u.username FROM sos_alerts s"
        " LEFT JOIN locations l ON l.id = s.location_id"
        " LEFT JOIN users u ON u.id = s.user_id"
        " ORDER BY (s.status='open') DESC, s.id DESC LIMIT 100")]


def update_sos(con, alert_id, status):
    if status not in ("acknowledged", "closed"):
        raise ValueError("Unknown action.")
    cur = con.execute("UPDATE sos_alerts SET status=? WHERE id=?", (status, alert_id))
    con.commit()
    if not cur.rowcount:
        raise ValueError("No such alert.")
    return {"id": alert_id, "status": status}


def open_sos_count(con):
    return con.execute("SELECT count(*) FROM sos_alerts WHERE status='open'").fetchone()[0]


def log_search(con, from_id, to_id, user_id):
    con.execute("INSERT INTO searches (from_id,to_id,user_id,at) VALUES (?,?,?,?)",
                (from_id, to_id, user_id, _now()))
    con.commit()


def stats(con, limit=8):
    def top(column):
        return [dict(r) for r in con.execute(
            f"SELECT s.{column} AS id, COALESCE(l.name, s.{column} || ' (deleted)') AS name,"
            f" count(*) AS n FROM searches s LEFT JOIN locations l ON l.id = s.{column}"
            f" GROUP BY s.{column} ORDER BY n DESC, name LIMIT ?", (limit,))]

    total = con.execute("SELECT count(*) FROM searches").fetchone()[0]
    return {
        "total_lookups": total,
        "students": con.execute("SELECT count(*) FROM users WHERE role='student'").fetchone()[0],
        "locations": con.execute("SELECT count(*) FROM locations").fetchone()[0],
        "paths": con.execute("SELECT count(*) FROM edges").fetchone()[0],
        "top_destinations": top("to_id"),
        "top_starts": top("from_id"),
        "open_sos": open_sos_count(con),
        "pending_items": con.execute(
            "SELECT count(*) FROM lost_found WHERE status='pending'").fetchone()[0],
    }

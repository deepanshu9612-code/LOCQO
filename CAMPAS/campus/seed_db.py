"""Build campus.db (SQLite) — the LOCQO campus graph for K.R. Mangalam University.

Nodes = places (rooms, blocks, facilities, outdoor waypoints, corridors, stairs).
Edges = walkable connections (walk / door / stairs).
Seeded from reference_docs (layout plan + labs list) and data/CAMPUS_METADATA.md.
Coarse v1 graph: block -> floor-corridor -> room. Densify per-floor later.

Run:  python3 seed_db.py   ->   writes ./campus.db
"""
import json
import math
import os
import sqlite3

DB = os.environ.get("LOCQO_DB", os.path.join(os.path.dirname(__file__), "campus.db"))

# ---------------------------------------------------------------------------
# NODES.  (id, name, type, level, block, floor, room, x, y, aliases, tour_scene)
# Coordinates: outdoor uses a shared 0..100 (x) by 0..140 (y) portrait plane,
# south (main gate) at high y. Each indoor floor uses its own 0..100 plane.
# ---------------------------------------------------------------------------

# --- Outdoor level: campus waypoints & facilities (from the layout plan) ---
OUTDOOR = [
    # id, name, type, x, y, aliases, tour_scene
    ("main-gate",        "Main Gate",              "gate",      50, 134, ["entrance", "gate", "entry"], "5130"),
    ("security",         "Security Checkpoint",    "junction",  50, 126, ["guard"], "4356"),
    ("atm",              "ATM",                    "amenity",   39, 130, ["cash", "bank"], None),
    ("visitor-parking",  "Visitor Parking",        "parking",   27, 132, ["guest parking"], "8671"),
    ("student-parking",  "Student Parking",        "parking",   73, 132, ["bike parking"], "8562"),
    ("block-a",          "Block A",                "block",     50, 112, ["a block", "admin block"], None),
    ("canteen",          "Canteen",                "eatery",    50, 100, ["food", "cafeteria", "mess"], "2069"),
    ("quad",             "Central Courtyard",      "junction",  50, 86,  ["quad", "courtyard"], None),
    ("block-b",          "Block B",                "block",     35, 86,  ["b block"], None),
    ("block-c",          "Block C",                "block",     65, 86,  ["c block"], None),
    ("chinese-outlet",   "Chinese Outlet",         "eatery",    78, 94,  ["chinese food"], None),
    ("nescafe-outlet",   "Nescafe Outlet",         "eatery",    78, 80,  ["coffee", "cafe"], "7067"),
    ("electricity",      "Electricity Substation", "utility",   88, 88,  ["power"], None),
    ("football-central", "Football Ground",        "ground",    52, 62,  ["football", "soccer field"], "2018"),
    ("basketball",       "Basketball Court",       "ground",    28, 60,  ["basketball"], "8460"),
    ("cricket",          "Cricket Ground",         "ground",    28, 72,  ["cricket"], "2443"),
    ("boys-hostel",      "Boys Hostel",            "hostel",    12, 58,  ["vivekanand hostel", "boys"], "9017"),
    ("girls-hostel",     "Girls Hostel",           "hostel",    12, 72,  ["gayatri hostel", "girls"], "6683"),
    ("driveway",         "North Driveway",         "junction",  50, 44,  ["road"], "9980"),
    ("block-d",          "Block D",                "block",     54, 26,  ["d block"], None),
    ("football-d",       "Football Ground (North)","ground",    32, 28,  ["north football"], None),
    ("bus-parking",      "Bus / Vehicle Parking",  "parking",   88, 106, ["bus stand"], None),
]

# --- Indoor: block -> floors present -> corridor node per floor ---
# Only floors evidenced by the labs list are modelled.
BLOCK_FLOORS = {"A": [0], "B": [0, 1, 2, 3, 4, 5], "C": [0, 1, 4]}

# --- Rooms (from labs list JPEG). lab_id, room_code, block, floor, tour_scene ---
LABS = [
    ("lab-1",  "A009", "A", 0, None),
    ("lab-3",  "A011", "A", 0, None),
    ("lab-4",  "A014", "A", 0, None),
    ("lab-5",  "B102", "B", 1, "9981"),   # Computer Lab (illustrative tour link)
    ("lab-6",  "B402", "B", 4, None),
    ("lab-8",  "C015", "C", 0, None),
    ("lab-9",  "B005", "B", 0, None),
    ("lab-10", "A Library", "A", 0, None),
    ("lab-11", "A Library", "A", 0, None),
    ("lab-12", "C102", "C", 1, None),
    ("lab-13", "C404", "C", 4, None),
    ("lab-14", "B508", "B", 5, None),
    ("lab-15", "B202", "B", 2, "3207"),
    ("lab-16", "B207", "B", 2, None),
    ("lab-17", "A Library", "A", 0, None),
    ("lab-19", "B504", "B", 5, None),
    ("lab-20", "B517", "B", 5, None),
    ("lab-21", "B205", "B", 2, None),
    ("lab-22", "B209", "B", 2, None),
]


def dist(a, b):
    """Euclidean distance between two (x, y) nodes, rounded to a positive int."""
    return max(1, round(math.hypot(a[0] - b[0], a[1] - b[1])))


def build():
    nodes = []   # dict rows
    edges = []   # (a, b, weight, kind)
    xy = {}      # id -> (x, y) for outdoor distance calc

    # Outdoor nodes (block nodes carry their letter so the map can label them)
    for nid, name, typ, x, y, aliases, scene in OUTDOOR:
        blk = nid.split("-")[1].upper() if typ == "block" else None
        nodes.append(dict(id=nid, name=name, type=typ, level="outdoor", block=blk,
                          floor=None, room=None, x=x, y=y,
                          aliases=json.dumps(aliases), tour_scene=scene))
        xy[nid] = (x, y)

    # Outdoor walkways (undirected). Weight = distance between endpoints.
    outdoor_links = [
        ("main-gate", "security"), ("security", "atm"),
        ("security", "visitor-parking"), ("security", "student-parking"),
        ("security", "block-a"), ("block-a", "canteen"), ("canteen", "quad"),
        ("quad", "block-b"), ("quad", "block-c"), ("quad", "football-central"),
        ("block-c", "chinese-outlet"), ("block-c", "nescafe-outlet"),
        ("block-c", "electricity"), ("block-c", "bus-parking"),
        ("student-parking", "bus-parking"),
        ("football-central", "basketball"), ("basketball", "cricket"),
        ("football-central", "boys-hostel"), ("boys-hostel", "girls-hostel"),
        ("football-central", "driveway"), ("driveway", "block-d"),
        ("block-d", "football-d"),
    ]
    for a, b in outdoor_links:
        edges.append((a, b, float(dist(xy[a], xy[b])), "walk"))

    # Indoor: per block, a corridor node per floor + stairs between consecutive
    # modelled floors + a door from the block's outdoor entrance to floor 0.
    for block, floors in BLOCK_FLOORS.items():
        prev = None
        for f in floors:
            cid = f"{block.lower()}-corr-{f}"
            nodes.append(dict(id=cid, name=f"Block {block} · Floor {f} corridor",
                              type="corridor", level=f"{block}-{f}", block=block,
                              floor=f, room=None, x=50, y=50,
                              aliases=json.dumps([]), tour_scene=None))
            if prev is None:
                # door: outdoor block entrance -> floor 0 corridor
                edges.append((f"block-{block.lower()}", cid, 3.0, "door"))
            else:
                # stairs between the previous modelled floor and this one.
                span = f - prev_floor
                edges.append((prev, cid, 6.0 * span, "stairs"))
            prev = cid
            prev_floor = f

    # Library lives inside Block A (ground floor).
    nodes.append(dict(id="library", name="Central Library", type="library",
                      level="A-0", block="A", floor=0, room="A Library",
                      x=75, y=50, aliases=json.dumps(["library", "books"]),
                      tour_scene="9937"))
    edges.append(("a-corr-0", "library", 4.0, "walk"))

    # Rooms attach to their block-floor corridor (library labs attach to library).
    room_x = {}  # simple spread along the corridor per floor
    for lab_id, room, block, floor, scene in LABS:
        if room == "A Library":
            edges.append(("library", lab_id, 3.0, "walk"))
            name = f"{lab_id.replace('-', ' ').title()} (Library)"
            level, x, y = "A-0", 78, 50
        else:
            corr = f"{block.lower()}-corr-{floor}"
            edges.append((corr, lab_id, 4.0, "walk"))
            name = f"{lab_id.replace('-', ' ').title()} ({room})"
            # spread rooms horizontally so they do not overlap on the floor plan
            k = room_x.get((block, floor), 0)
            room_x[(block, floor)] = k + 1
            level, x, y = f"{block}-{floor}", 25 + (k % 5) * 14, 40 + (k // 5) * 20
        nodes.append(dict(id=lab_id, name=name, type="lab", level=level,
                          block=block, floor=floor, room=room, x=x, y=y,
                          aliases=json.dumps([room.lower(), lab_id.replace("-", " ")]),
                          tour_scene=scene))

    return nodes, edges


def write_db(nodes, edges):
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.executescript(
        """
        CREATE TABLE locations (
            id         TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            type       TEXT NOT NULL,
            level      TEXT NOT NULL,
            block      TEXT,
            floor      INTEGER,
            room       TEXT,
            x          REAL NOT NULL,
            y          REAL NOT NULL,
            aliases    TEXT NOT NULL DEFAULT '[]',
            tour_scene TEXT
        );
        CREATE TABLE edges (
            a      TEXT NOT NULL REFERENCES locations(id),
            b      TEXT NOT NULL REFERENCES locations(id),
            weight REAL NOT NULL,
            kind   TEXT NOT NULL
        );
        CREATE INDEX idx_edges_a ON edges(a);
        CREATE INDEX idx_edges_b ON edges(b);

        -- accounts. username is NOCASE so "Ekta" and "ekta" cannot both exist.
        CREATE TABLE users (
            id         INTEGER PRIMARY KEY,
            username   TEXT NOT NULL UNIQUE COLLATE NOCASE,
            name       TEXT NOT NULL,
            role       TEXT NOT NULL CHECK (role IN ('student','admin')),
            pw_salt    TEXT NOT NULL,
            pw_hash    TEXT NOT NULL,
            active     INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE sessions (
            token      TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        -- notices and events are one thing: an entry with no starts_at is a standing
        -- notice (the banner), one with a date is an upcoming event.
        CREATE TABLE announcements (
            id          INTEGER PRIMARY KEY,
            body        TEXT NOT NULL,
            author_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            active      INTEGER NOT NULL DEFAULT 1,
            starts_at   TEXT,
            location_id TEXT REFERENCES locations(id) ON DELETE SET NULL,
            created_at  TEXT NOT NULL
        );

        -- recurring weekly slots. Times are minutes since midnight so "is this room
        -- free now" is an integer comparison, with no date parsing anywhere.
        CREATE TABLE timetable (
            id          INTEGER PRIMARY KEY,
            location_id TEXT NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
            weekday     INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),  -- 0 = Monday
            start_min   INTEGER NOT NULL CHECK (start_min BETWEEN 0 AND 1439),
            end_min     INTEGER NOT NULL CHECK (end_min BETWEEN 1 AND 1440),
            title       TEXT NOT NULL,
            CHECK (end_min > start_min)
        );

        -- students post; nothing is visible until an admin approves it
        CREATE TABLE lost_found (
            id          INTEGER PRIMARY KEY,
            kind        TEXT NOT NULL CHECK (kind IN ('lost','found')),
            title       TEXT NOT NULL,
            details     TEXT,
            location_id TEXT REFERENCES locations(id) ON DELETE SET NULL,
            contact     TEXT,
            user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
            status      TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','approved','resolved','rejected')),
            created_at  TEXT NOT NULL
        );

        -- an in-app alert to admins. This does NOT reach emergency services.
        CREATE TABLE sos_alerts (
            id          INTEGER PRIMARY KEY,
            user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
            location_id TEXT REFERENCES locations(id) ON DELETE SET NULL,
            note        TEXT,
            status      TEXT NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open','acknowledged','closed')),
            created_at  TEXT NOT NULL
        );
        CREATE INDEX idx_timetable_loc ON timetable(location_id, weekday);
        CREATE INDEX idx_lost_status ON lost_found(status);
        -- route lookups, for the admin analytics tab. Deliberately NOT foreign-keyed to
        -- locations: the stats must survive an admin deleting a location.
        CREATE TABLE searches (
            id      INTEGER PRIMARY KEY,
            from_id TEXT NOT NULL,
            to_id   TEXT NOT NULL,
            user_id INTEGER,
            at      TEXT NOT NULL
        );
        CREATE INDEX idx_sessions_user ON sessions(user_id);
        CREATE INDEX idx_searches_to ON searches(to_id);
        """
    )
    con.executemany(
        "INSERT INTO locations (id,name,type,level,block,floor,room,x,y,aliases,tour_scene)"
        " VALUES (:id,:name,:type,:level,:block,:floor,:room,:x,:y,:aliases,:tour_scene)",
        nodes,
    )
    con.executemany("INSERT INTO edges (a,b,weight,kind) VALUES (?,?,?,?)", edges)
    con.commit()

    # sanity: every edge endpoint must exist as a node
    ids = {n["id"] for n in nodes}
    for a, b, _, _ in edges:
        assert a in ids and b in ids, f"edge references missing node: {a} / {b}"
    con.close()
    return len(nodes), len(edges)


def seed_admin(username="admin"):
    """Create the one bootstrap admin. Password from $ADMIN_PASSWORD, else generated."""
    import secrets

    import auth  # imported here so `build()` stays importable without the auth module

    password = os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(12)
    con = auth.connect()
    try:
        auth.create_user(con, username, "Campus Admin", password, role="admin")
        con.commit()
    finally:
        con.close()
    return username, password


if __name__ == "__main__":
    import sys

    if os.path.exists(DB) and "--force" not in sys.argv:
        raise SystemExit(
            f"{DB} already exists — refusing to overwrite.\n"
            "Re-seeding wipes every account and any campus edits admins made in the browser.\n"
            "Pass --force if that is really what you want."
        )
    nodes, edges = build()
    n, e = write_db(nodes, edges)
    user, pw = seed_admin()
    print(f"Wrote {DB}: {n} locations, {e} edges")
    print(f"Admin account: {user} / {pw}")
    print("Students create their own accounts at /login.")

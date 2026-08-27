"""LOCQO web server — stdlib only (no dependencies).

Serves the graphical front end + a JSON API over the routing engine.
Login is required for everything except the login page itself.
Run:  python3 app.py   ->   http://localhost:8000
"""
import json
import os
import sqlite3
import traceback
from datetime import datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import admin
import auth
import routing

ROOT = os.path.dirname(__file__)
STATIC = os.path.join(ROOT, "static")
PORT = int(os.environ.get("PORT", "8000"))

# The only paths a logged-out browser may fetch. Everything else — including
# index.html and app.js — is behind the session check.
PUBLIC = {"/login", "/login.html", "/login.js", "/style.css", "/favicon.ico"}
ADMIN_PAGES = {"/admin", "/admin.html", "/admin.js"}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=STATIC, **kw)

    # ---- plumbing --------------------------------------------------------
    def _json(self, obj, status=200, cookie=None):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        # Without this the stdlib handler sends only Last-Modified, so browsers apply
        # heuristic caching and will re-render a logged-in page after logout (Back button
        # on a shared campus machine). Everything here is small; nothing needs caching.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _redirect(self, to):
        self.send_response(302)
        self.send_header("Location", to)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _body(self):
        """Parsed JSON body.

        Demanding the JSON content-type is half the CSRF defence (SameSite=Strict on the
        cookie is the other half): a cross-site HTML form cannot set this header without
        tripping a preflight.
        """
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            raise ValueError("Expected application/json.")
        size = int(self.headers.get("Content-Length") or 0)
        if not 0 < size <= 64_000:
            raise ValueError("Bad request body.")
        body = json.loads(self.rfile.read(size).decode())
        # every handler below does body.get(...) — a list, string or null would throw
        # there and surface as a 500 instead of a plain "you sent the wrong thing"
        if not isinstance(body, dict):
            raise ValueError("Expected a JSON object.")
        return body

    # An unhandled exception in a handler would otherwise drop the connection with no
    # response at all — the browser just sees the socket close. Always answer something.
    def do_GET(self):
        try:
            return self._get()
        except Exception:
            traceback.print_exc()
            return self._json({"error": "server error"}, 500)

    def do_POST(self):
        try:
            return self._post()
        except Exception:
            traceback.print_exc()
            return self._json({"error": "server error"}, 500)

    # ---- GET -------------------------------------------------------------
    def _get(self):
        path = urlparse(self.path).path

        if path == "/api/me":
            user = auth.current_user(self)
            return self._json(auth.public(user) if user else {"error": "not signed in"},
                              200 if user else 401)

        if path in PUBLIC:
            if path == "/login":
                self.path = "/login.html"
            return super().do_GET()

        user = auth.current_user(self)
        if not user:
            if path.startswith("/api/"):
                return self._json({"error": "not signed in"}, 401)
            return self._redirect("/login")

        if path.startswith("/api/admin/"):
            if user["role"] != "admin":
                return self._json({"error": "admins only"}, 403)
            return self._admin_get(path)

        if path == "/api/locations":
            return self._json(routing.destinations())
        if path == "/api/graph":
            return self._json(_graph())
        if path == "/api/announcements":
            return self._json(_with_db(admin.list_announcements))
        if path == "/api/route":
            return self._route(user)
        if path == "/api/free-rooms":
            return self._free_rooms()
        if path == "/api/lost-found":
            return self._json(_with_db(admin.list_lost_found, user_id=user["id"]))
        if path == "/api/emergency":
            # numbers a person dials themselves — the app cannot place the call
            return self._json({"contacts": admin.EMERGENCY_CONTACTS,
                               "security_id": "security"})

        if path in ADMIN_PAGES:
            if user["role"] != "admin":
                return self._redirect("/")
            if path == "/admin":
                self.path = "/admin.html"
        elif path == "/campus":
            self.path = "/campus.html"
        elif path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def _free_rooms(self):
        """Defaults to right now, on the server's clock."""
        q = parse_qs(urlparse(self.path).query)
        now = datetime.now()
        try:
            weekday = int(q.get("day", [now.weekday()])[0])
            minute = int(q.get("time", [now.hour * 60 + now.minute])[0])
        except ValueError:
            return self._json({"error": "day and time must be numbers"}, 400)
        if not (0 <= weekday <= 6 and 0 <= minute <= 1439):
            return self._json({"error": "day must be 0–6 and time 0–1439"}, 400)
        return self._json(_with_db(admin.free_rooms, weekday, minute))

    def _route(self, user):
        q = parse_qs(urlparse(self.path).query)
        frm, to = q.get("from", [""])[0], q.get("to", [""])[0]
        if not frm or not to:
            return self._json({"error": "from and to are required"}, 400)
        result = routing.route(frm, to)
        if "error" not in result:
            _with_db(admin.log_search, frm, to, user["id"])
        return self._json(result)

    def _admin_get(self, path):
        name = path[len("/api/admin/"):]
        con = routing.connect()
        try:
            if name == "locations":
                return self._json(admin.list_locations(con))
            if name == "edges":
                return self._json(admin.list_edges(con))
            if name == "users":
                return self._json(admin.list_users(con))
            if name == "announcements":
                return self._json(admin.list_announcements(con, active_only=False))
            if name == "stats":
                return self._json(admin.stats(con))
            if name == "timetable":
                return self._json(admin.list_timetable(con))
            if name == "lost-found":
                return self._json(admin.list_lost_found(
                    con, statuses=("pending", "approved", "resolved", "rejected")))
            if name == "sos":
                return self._json(admin.list_sos(con))
            return self._json({"error": "not found"}, 404)
        finally:
            con.close()

    # ---- POST ------------------------------------------------------------
    def _post(self):
        path = urlparse(self.path).path
        try:
            body = self._body()
        except ValueError as e:
            return self._json({"error": str(e)}, 400)

        if path == "/api/signup":
            return self._signup(body)
        if path == "/api/login":
            return self._login(body)

        user = auth.current_user(self)
        if not user:
            return self._json({"error": "not signed in"}, 401)
        if path == "/api/logout":
            auth.logout(self)
            return self._json({"ok": True}, cookie=auth.clear_cookie_header())

        # things any signed-in student may do
        try:
            if path == "/api/lost-found":
                return self._json(_with_db(admin.create_lost_found, user["id"], body))
            if path == "/api/lost-found/resolve":
                return self._json(_with_db(
                    admin.moderate_lost_found, body.get("id"), "resolved",
                    actor_id=user["id"], is_admin=user["role"] == "admin"))
            if path == "/api/sos":
                return self._json(_with_db(admin.raise_sos, user["id"], body))
        except ValueError as e:
            return self._json({"error": str(e)}, 400)

        if path.startswith("/api/admin/"):
            if user["role"] != "admin":
                return self._json({"error": "admins only"}, 403)
            return self._admin_post(path, body, user)
        return self._json({"error": "not found"}, 404)

    def _signup(self, body):
        con = routing.connect()
        try:
            # role is hardcoded: self-signup can only ever mint a student, whatever
            # the request body claims.
            auth.create_user(con, body.get("username"), body.get("name"),
                             body.get("password"), role="student")
            user, token = auth.login(con, body.get("username"), body.get("password"),
                                     self.client_address[0])
            con.commit()
        except ValueError as e:
            return self._json({"error": str(e)}, 400)
        finally:
            con.close()
        return self._json(auth.public(user), cookie=auth.cookie_header(token))

    def _login(self, body):
        con = routing.connect()
        try:
            user, token = auth.login(con, body.get("username"), body.get("password"),
                                     self.client_address[0])
            con.commit()
        except ValueError as e:
            return self._json({"error": str(e)}, 401)
        finally:
            con.close()
        return self._json(auth.public(user), cookie=auth.cookie_header(token))

    def _admin_post(self, path, body, user):
        name = path[len("/api/admin/"):]
        con = routing.connect()
        try:
            if name == "locations":
                return self._json(admin.create_location(con, body))
            if name == "locations/update":
                return self._json(admin.update_location(con, body))
            if name == "locations/delete":
                return self._json(admin.delete_location(con, body.get("id")))
            if name == "edges":
                return self._json(admin.create_edge(con, body))
            if name == "edges/delete":
                return self._json(admin.delete_edge(con, body.get("a"), body.get("b")))
            if name == "users":
                return self._json(admin.create_user(con, body))
            if name == "users/update":
                return self._json(admin.update_user(con, user["id"], body))
            if name == "announcements":
                return self._json(admin.create_announcement(
                    con, user["id"], body.get("body"),
                    body.get("starts_at"), body.get("location_id")))
            if name == "announcements/delete":
                return self._json(admin.delete_announcement(con, body.get("id")))
            if name == "timetable":
                return self._json(admin.create_slot(con, body))
            if name == "timetable/delete":
                return self._json(admin.delete_slot(con, body.get("id")))
            if name == "lost-found/moderate":
                return self._json(admin.moderate_lost_found(
                    con, body.get("id"), body.get("status"), is_admin=True))
            if name == "lost-found/delete":
                return self._json(admin.delete_lost_found(con, body.get("id")))
            if name == "sos/update":
                return self._json(admin.update_sos(con, body.get("id"), body.get("status")))
            return self._json({"error": "not found"}, 404)
        except ValueError as e:
            return self._json({"error": str(e)}, 400)
        except sqlite3.Error as e:
            # e.g. a FK constraint refusing to orphan an edge — the write is rejected
            # whole, and the admin gets a reason instead of a dropped connection.
            con.rollback()
            return self._json({"error": f"That change was rejected by the database ({e})."}, 400)
        finally:
            con.close()

    def log_message(self, *a):
        pass  # quiet


def _with_db(fn, *a, **kw):
    con = routing.connect()
    try:
        return fn(con, *a, **kw)
    finally:
        con.close()


def _graph():
    """Outdoor base-map nodes + walkways for the front end to draw."""
    con = routing.connect()
    try:
        nodes = [dict(r) for r in con.execute(
            "SELECT id,name,type,level,block,floor,x,y,tour_scene FROM locations")]
        edges = [dict(r) for r in con.execute("SELECT a,b,kind FROM edges")]
        return {"nodes": nodes, "edges": edges}
    finally:
        con.close()


if __name__ == "__main__":
    if not os.path.exists(routing.DB):
        raise SystemExit(f"{routing.DB} not found — run: python3 seed_db.py")
    if not _with_db(lambda con: con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()):
        raise SystemExit("This database predates accounts — rebuild it: python3 seed_db.py --force")
    print(f"LOCQO running at http://localhost:{PORT}  (Ctrl-C to stop)")
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()

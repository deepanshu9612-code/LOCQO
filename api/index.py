"""Vercel entrypoint.

Vercel loads the `handler` class from this file and, via the catch-all rewrite in
vercel.json, serves every path through it. Nothing else changes: `python3 app.py`
still runs the app locally.
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)  # app.py / auth.py / routing.py live one level up

# A serverless disk is read-only apart from /tmp, and almost every request writes
# (sessions on login, search logs, lost+found, SOS) — sqlite also needs to create a
# rollback journal beside the file. So run against a copy in /tmp.
# ponytail: /tmp is per-instance and disposable — signups, SOS alerts and admin edits
#           are lost when the instance recycles, and a second instance starts from the
#           seeded copy (so a session opened on one may not be recognised by another).
#           Point LOCQO_DB at hosted sqlite/Postgres when the data has to persist.
DB = "/tmp/campus.db"
os.environ["LOCQO_DB"] = DB                    # routing.DB is read at import time
os.environ.setdefault("SECURE_COOKIES", "1")   # ...as is auth.SECURE_COOKIE; Vercel is https
if not os.path.exists(DB):
    shutil.copyfile(os.path.join(ROOT, "campus.db"), DB)

from app import Handler  # noqa: E402


# Vercel schedules a Python function only if its AST analyser finds a top-level `app`,
# `application` or `handler` here — and for `handler` it looks for a real class
# statement, not an aliased import (`... import Handler as handler` is NOT detected,
# which silently produced no function at all and 404'd every path).
class handler(Handler):
    pass

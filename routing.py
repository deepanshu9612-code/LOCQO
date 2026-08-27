"""LOCQO routing engine: shortest path + step-by-step directions over campus.db."""
import heapq
import json
import math
import os
import sqlite3

DB = os.environ.get("LOCQO_DB", os.path.join(os.path.dirname(__file__), "campus.db"))

# outdoor plane unit -> metres (campus ~100 units wide ~= ~350 m across)
UNIT_M = 3.0
WALK_M_PER_MIN = 70.0
_COMPASS = ["north", "north-east", "east", "south-east",
            "south", "south-west", "west", "north-west"]


def connect():
    """Shared connection factory for every module that touches campus.db."""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")  # off by default; the FKs are inert without it
    return con


def load_graph(con):
    """Return (nodes_by_id, adjacency). adjacency[id] = [(neighbor, weight, kind)]."""
    nodes = {r["id"]: dict(r) for r in con.execute("SELECT * FROM locations")}
    adj = {nid: [] for nid in nodes}
    for e in con.execute("SELECT a, b, weight, kind FROM edges"):
        if e["a"] not in adj or e["b"] not in adj:
            continue  # orphaned edge: skip it rather than 500 every route on the campus
        adj[e["a"]].append((e["b"], e["weight"], e["kind"]))
        adj[e["b"]].append((e["a"], e["weight"], e["kind"]))  # undirected
    return nodes, adj


def shortest_path(adj, start, goal):
    """Dijkstra. Returns (path_list, total_weight) or (None, inf) if unreachable."""
    if start == goal:
        return [start], 0.0
    dist = {start: 0.0}
    prev = {}
    pq = [(0.0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == goal:
            path = [u]
            while u in prev:
                u = prev[u]
                path.append(u)
            return path[::-1], d
        if d > dist.get(u, math.inf):
            continue
        for v, w, _ in adj[u]:
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    return None, math.inf


def _compass(a, b):
    dx, dy = b["x"] - a["x"], b["y"] - a["y"]
    ang = (math.degrees(math.atan2(dx, -dy)) + 360) % 360  # 0=N, y grows south
    return _COMPASS[round(ang / 45) % 8]


def _block_name(nodes, corridor_node):
    return f"Block {corridor_node['block']}"


def directions(nodes, adj, path):
    """Turn a node-id path into human step strings + a distance/time estimate."""
    if not path:
        return {"steps": [], "distance_m": 0, "time_min": 0, "levels": []}
    start, end = nodes[path[0]], nodes[path[-1]]
    steps = [f"Start at {start['name']}."]
    total = 0.0

    # edge kind/weight lookup for consecutive path pairs
    for u_id, v_id in zip(path, path[1:]):
        u, v = nodes[u_id], nodes[v_id]
        kind, w = _edge_between(adj, u_id, v_id)
        total += w
        is_last = v_id == path[-1]

        if kind == "door":
            if v["level"] != "outdoor":              # walking inside
                steps.append(f"Enter {_block_name(nodes, v)}.")
            else:                                      # walking out
                steps.append(f"Exit {_block_name(nodes, u)} to the campus.")
        elif kind == "stairs":
            updown = "up" if (v["floor"] or 0) > (u["floor"] or 0) else "down"
            steps.append(f"Take the stairs {updown} to Floor {v['floor']}.")
        elif u["level"] == "outdoor" and v["level"] == "outdoor":
            if is_last:
                continue  # arrival line covers it
            if v["type"] == "junction":
                steps.append(f"Head {_compass(u, v)} past {v['name']}.")
            else:
                steps.append(f"Head {_compass(u, v)} to {v['name']}.")
        else:  # indoor walk (corridor <-> room/library)
            if v["type"] == "corridor" or is_last:
                continue  # pass-through / handled by arrival
            steps.append(f"Go to {v['name']}.")

    code = end.get("room")
    room = f" (Room {code})" if code and code != "A Library" and code not in end["name"] else ""
    steps.append(f"Arrive at {end['name']}{room}.")

    metres = round(total * UNIT_M)
    return {
        "steps": steps,
        "distance_m": metres,
        "time_min": max(1, round(metres / WALK_M_PER_MIN)),
        "levels": _levels_traversed(nodes, path),
    }


def _edge_between(adj, u_id, v_id):
    """kind + weight of the edge joining two adjacent path nodes."""
    for neighbor, w, kind in adj[u_id]:
        if neighbor == v_id:
            return kind, w
    return "walk", 1.0


def _levels_traversed(nodes, path):
    seen = []
    for nid in path:
        lv = nodes[nid]["level"]
        if lv not in seen:
            seen.append(lv)
    return seen


def route(start, goal):
    """Top-level: returns a dict with path, steps, and estimate (or an error)."""
    con = connect()
    try:
        nodes, adj = load_graph(con)
        if start not in nodes or goal not in nodes:
            return {"error": "unknown location", "start": start, "goal": goal}
        path, _ = shortest_path(adj, start, goal)
        if path is None:
            return {"error": "no route found", "start": start, "goal": goal}
        result = directions(nodes, adj, path)
        result["path"] = path
        result["from"] = nodes[start]["name"]
        result["to"] = nodes[goal]["name"]
        return result
    finally:
        con.close()


def destinations():
    """Pickable locations for the From/To dropdowns (excludes internal waypoints)."""
    con = connect()
    try:
        rows = con.execute(
            "SELECT id,name,type,block,floor,room,tour_scene FROM locations "
            "WHERE type NOT IN ('corridor','junction') ORDER BY type, name"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


if __name__ == "__main__":
    import sys
    r = route(sys.argv[1], sys.argv[2]) if len(sys.argv) == 3 else route("lab-1", "lab-15")
    print(json.dumps(r, indent=2))

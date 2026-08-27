# LOCQO — Campus Navigation Web App · Design Spec

**Date:** 2026-07-12
**Status:** approved direction, building v1
**One-liner:** A simple graphical web app for K.R. Mangalam University where a new student/visitor picks *where they are* and *where they want to go*, and gets step-by-step directions across the campus.

---

## 1. Decisions (locked with user)

| Topic | Decision |
|---|---|
| Core interaction | Two inputs — **From** (current location) + **To** (destination) → **Get directions**. Nothing else. |
| Navigation | **Static step-by-step** directions + a route drawn on a schematic map. No live GPS/blue-dot tracking. |
| Extras | **None** in v1 — no voice, no QR, no chatbot, no SOS, no lost&found, no events. Deferred. |
| Datastore | **SQLite** (`campus.db`), kept minimal. Swap to a "real" DB later. |
| Map data | **Hand-authored** by us (no official floor plans exist). |
| v1 coverage | Data we already have: **Blocks A–D**, the **19 labs** (real room codes), campus **facilities/grounds/hostels/gate/parking** from the layout plan. Coarse block→floor→room graph. |
| Survey editor | **Deferred.** Not needed for the coarse v1 graph. Revisit when densifying per-floor detail. |
| Stack | **Python + SQLite (stdlib)** engine + thin web layer. Frontend is a simple graphical page. |
| Scope size | **Small.** Smallest thing that delivers correct two-input directions. |

## 2. Data model (SQLite)

Two tables — a graph.

**`locations`** (nodes): `id` (PK, text), `name`, `type` (gate/block/lab/eatery/ground/hostel/parking/amenity/utility/corridor/stairs/junction/library), `level` (`outdoor`, `A-0`, `B-2`, …), `block` (A–D, null outdoors), `floor` (int, null), `room` (text, null, e.g. `B202`), `x`, `y` (coords for drawing on that level), `aliases` (json text), `tour_scene` (text, null — deep-link id into the live 360° tour).

**`edges`** (walkable connections): `a`, `b` (FK → locations.id), `weight` (real), `kind` (`walk`/`door`/`stairs`/`lift`). Undirected (stored once, traversed both ways).

The graph spans levels: `door` edges join a block's outdoor entrance to its floor-0 corridor; `stairs` edges join a block's consecutive floor corridors; rooms attach to their floor corridor. A cross-campus route (e.g. Lab 1 in A → Lab 15 in B202) is one shortest path: room → A-0 → block-A entrance → outdoor walkways → block-B entrance → stairs to floor 2 → Lab 15.

Seeded from `data/CAMPUS_METADATA.md` + `reference_docs/labs list.jpeg` + `data/tour_scenes.json`.

## 3. Engine (Python)

- **Shortest path:** Dijkstra over the edges (~40 lines, stdlib only). A few hundred nodes → instant.
- **Directions:** walk the path node-by-node → human steps.
  - Outdoor `walk`: "Head {N/E/S/W} to {landmark}" (compass from node coordinates).
  - `door`: "Enter Block {X}."
  - `stairs`: "Take the stairs {up/down} to Floor {n}."
  - arrival: "Arrive at {room} — {name}."
- **Estimate:** sum of edge weights → approximate distance (clearly marked `~`), plus step count.

## 4. Web layer & screens (mobile-first)

- **Home:** brand (LOCQO), two searchable selects (From, To) over all routable locations, **Get Directions** button.
- **Result:** the route drawn on a schematic campus map (outdoor level + a per-floor strip when the route goes indoors) **and** the numbered step list with the distance estimate. Where a location has a `tour_scene`, a **View 360°** link opens the live tour.

Routable locations for v1 = the located ones (blocks, 19 labs, facilities, grounds, hostels, gate, parking, food outlets). Tour scenes without a known block/floor are **not** routable yet (honest gap) but may decorate located nodes.

## 5. Explicitly out of scope for v1

Voice, QR, chatbot, empty-classroom finder, lost & found, events/notices, SOS, faculty locator, live positioning, user accounts, a backend database beyond SQLite, and full per-floor surveyed corridor geometry.

## 6. Testing

- One assert-based self-check: a known From→To pair returns the expected node sequence, a sane step count, and a monotonic distance. This is the thing that must never silently break when the graph is edited.

## 7. Future (not now)

Densify the graph per floor (optionally via a click-to-place survey editor), map the 175 tour scenes to real blocks/floors via on-site survey, add the deferred features behind a real backend, place QR anchors to auto-set "From".

## 8. Data provenance

See `data/CAMPUS_METADATA.md` — every fact tagged `[F]` layout/labs (authoritative), `[S]` scraped site, `[T]` 360 tour, `[I]` inference. No room numbers invented; only the 19 from the labs list are treated as ground truth.

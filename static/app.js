const SVGNS = "http://www.w3.org/2000/svg";
const TOUR_URL = "https://tourmkr.com/F1Zr0N570h"; // official 360° tour

const $ = (id) => document.getElementById(id);
let byName = {};        // lowercased display name -> id
let locById = {};       // id -> location row (block, floor, room, tour_scene)
let outdoor = {};       // id -> outdoor node {x,y,name,type,block}
let blockFloors = {};   // "B" -> [0,1,2,3,4,5]  (from corridor nodes)
let CENTER_X = 50;
let VB = null;          // [minX, minY, width, height] — labels must stay inside it
let layers = {};        // svg <g> layers: edges, route, nodes, labels, pins

// ---- boot ----------------------------------------------------------------
boot();
async function boot() {
  const who = await fetch("/api/me");
  if (!who.ok) return location.replace("/login");   // session gone or never was
  const user = await who.json();
  $("who").textContent = `${user.name} · ${user.role === "admin" ? "Admin" : "Student"}`;
  if (user.role === "admin") $("adminlink").hidden = false;

  try {
    const [locs, graph, notices] = await Promise.all([
      fetch("/api/locations").then((r) => r.json()),
      fetch("/api/graph").then((r) => r.json()),
      fetch("/api/announcements").then((r) => r.json()),
    ]);
    const dl = $("locs");
    locs.forEach((l) => {
      locById[l.id] = l;
      byName[l.name.toLowerCase()] = l.id;
      const o = document.createElement("option");
      o.value = l.name;
      dl.appendChild(o);
    });
    graph.nodes.forEach((n) => {
      if (n.type === "corridor" && n.block != null) {
        (blockFloors[n.block] ??= []).push(n.floor);
      }
    });
    for (const b in blockFloors) blockFloors[b].sort((a, z) => a - z);
    renderNotices(notices);
    drawBaseMap(graph);

    // ?to=<id> — how the campus hub hands a destination over ("Directions" on a card)
    const wanted = new URLSearchParams(location.search).get("to");
    if (wanted && locById[wanted]) {
      $("to").value = locById[wanted].name;
      $("from").focus();
    }
  } catch {
    $("msg").textContent = "Couldn’t load campus data. Is the server running?";
  }
}

$("logout").addEventListener("click", async () => {
  await fetch("/api/logout", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
  });
  location.replace("/login");
});

function renderNotices(list) {
  const box = $("notices");
  box.replaceChildren();
  if (!list || !list.length) { box.hidden = true; return; }
  list.forEach((n) => {
    const p = document.createElement("p");
    p.className = "notice";
    p.textContent = n.body;          // admin-authored text — never innerHTML
    box.appendChild(p);
  });
  box.hidden = false;
}

// ---- resolve typed text to a location id ---------------------------------
function resolve(text) {
  const t = text.trim().toLowerCase();
  if (byName[t]) return byName[t];
  const hit = Object.keys(byName).find((n) => n.startsWith(t) && t.length > 1);
  return hit ? byName[hit] : null;
}

// ---- form ----------------------------------------------------------------
$("swap").addEventListener("click", () => {
  [$("from").value, $("to").value] = [$("to").value, $("from").value];
});

$("reverse").addEventListener("click", () => {
  [$("from").value, $("to").value] = [$("to").value, $("from").value];
  $("nav-form").requestSubmit();
});

// quick-destination chips fill the "To" field (and route if a start is set)
document.querySelectorAll(".quick button").forEach((b) => {
  b.addEventListener("click", () => {
    $("to").value = b.dataset.name;
    clearInvalid($("to"));
    if ($("from").value.trim()) $("nav-form").requestSubmit();
    else $("from").focus();
  });
});

// clear the invalid state as soon as the user edits a field
["from", "to"].forEach((id) => $(id).addEventListener("input", () => clearInvalid($(id))));

$("nav-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("msg").textContent = "";
  const from = resolve($("from").value), to = resolve($("to").value);
  if (!from) return fail("from", "Pick a starting point from the list.");
  if (!to) return fail("to", "Pick a destination from the list.");
  if (from === to) return fail("to", "Start and destination are the same place.");

  const btn = document.querySelector(".go");
  btn.disabled = true; btn.textContent = "Finding route…";
  try {
    const r = await fetch(`/api/route?from=${from}&to=${to}`).then((x) => x.json());
    if (r.error) return fail("to", `No route found — ${r.error}.`);
    renderRoute(r, to);
  } catch {
    $("msg").textContent = "Something went wrong finding the route. Please try again.";
  } finally {
    btn.disabled = false; btn.textContent = "Get Directions";
  }
});

function fail(field, message) {
  $("msg").textContent = message;
  const f = $(field);
  f.setAttribute("aria-invalid", "true");
  f.focus();
}
function clearInvalid(f) { f.removeAttribute("aria-invalid"); }

// ---- render the directions -----------------------------------------------
function renderRoute(r, toId) {
  clearInvalid($("from")); clearInvalid($("to"));
  $("map-cap").hidden = true;
  $("r-from").textContent = r.from;
  $("r-to").textContent = r.to;
  $("r-dist").textContent = `~${r.distance_m} m`;
  $("r-time").textContent = `~${r.time_min} min walk`;
  $("r-steps").textContent = `${r.steps.length} steps`;

  const ol = $("steps");
  ol.replaceChildren();
  const dest = locById[toId] || {};
  r.steps.forEach((textStr, i) => {
    const li = document.createElement("li");
    const kind = stepKind(textStr);
    li.className = kind;
    const icon = document.createElement("span");
    icon.className = "step-ico"; icon.setAttribute("aria-hidden", "true");
    icon.textContent = STEP_ICON[kind];
    li.append(icon, document.createTextNode(textStr));
    if (i === r.steps.length - 1 && dest.tour_scene) {
      const a = document.createElement("a");
      a.className = "tour"; a.href = TOUR_URL; a.target = "_blank"; a.rel = "noopener";
      a.textContent = "View 360°";
      li.appendChild(a);
    }
    ol.appendChild(li);
  });

  drawRoute(r.path);
  // the S/E letters are gone from the map, so the route lives in the accessible name
  $("map").setAttribute("aria-label", `Campus map showing the route from ${r.from} to ${r.to}`);
  renderFloors(dest, r.levels);
  $("result").hidden = false;
  $("result").scrollIntoView({ behavior: "smooth", block: "start" });
}

const STEP_ICON = { start: "◉", walk: "↑", enter: "⇥", stairs: "⇡", arrive: "★" };
function stepKind(t) {
  if (/^Start/.test(t)) return "start";
  if (/^Enter|^Exit/.test(t)) return "enter";
  if (/^Take the stairs/.test(t)) return "stairs";
  if (/^Arrive/.test(t)) return "arrive";
  return "walk";
}

// ---- indoor floor-climb diagram (the signature element) ------------------
function renderFloors(dest, levels) {
  const el = $("floors");
  el.replaceChildren();
  const indoor = (levels || []).some((l) => /^[A-D]-\d/.test(l));
  const floors = dest.block && blockFloors[dest.block];
  if (!indoor || !floors || dest.floor == null) { el.hidden = true; return; }

  const visited = new Set((levels || [])
    .filter((l) => l.startsWith(dest.block + "-"))
    .map((l) => +l.split("-")[1]));

  const h = document.createElement("div");
  h.className = "floors-h";
  h.textContent = `Inside Block ${dest.block}`;
  el.appendChild(h);

  const stack = document.createElement("div");
  stack.className = "stack";
  [...floors].reverse().forEach((f) => {
    const row = document.createElement("div");
    row.className = "floor";
    if (f === dest.floor) row.classList.add("dest");
    else if (visited.has(f)) row.classList.add("via");
    const n = document.createElement("span");
    n.className = "floor-n"; n.textContent = f === 0 ? "G" : f;
    const tag = document.createElement("span");
    tag.className = "floor-tag";
    tag.textContent = f === dest.floor ? `${dest.name}` : f === 0 ? "Entrance" : "";
    row.append(n, tag);
    stack.appendChild(row);
  });
  el.append(stack);
  el.hidden = false;
}

// ---- base schematic map --------------------------------------------------
function drawBaseMap(graph) {
  const svg = $("map");
  ensureDefs(svg);
  const nodes = graph.nodes.filter((n) => n.level === "outdoor");
  nodes.forEach((n) => (outdoor[n.id] = n));
  const xs = nodes.map((n) => n.x), ys = nodes.map((n) => n.y);
  // wider side margins than top/bottom: labels sit beside their dots, not above them
  const padX = 24, padY = 8;
  const vb = [Math.min(...xs) - padX, Math.min(...ys) - padY,
              Math.max(...xs) - Math.min(...xs) + padX * 2,
              Math.max(...ys) - Math.min(...ys) + padY * 2];
  svg.setAttribute("viewBox", vb.join(" "));
  VB = vb;
  CENTER_X = vb[0] + vb[2] / 2;

  layers = {};
  // labels come last so they sit above the route pins, which are only drawn later and so
  // can't be fed into the label collision pass at boot
  ["edges", "route", "nodes", "pins", "labels"].forEach((k) => {
    layers[k] = el("g"); layers[k].setAttribute("data-layer", k); svg.appendChild(layers[k]);
  });

  graph.edges.forEach((e) => {
    const a = outdoor[e.a], b = outdoor[e.b];
    if (a && b) layers.edges.appendChild(line(a.x, a.y, b.x, b.y, "m-edge"));
  });

  // shapes first; then resolve label positions to avoid collisions. Grounds are labelled
  // outside like any other point — their names are far wider than the 13-unit rect.
  const obstacles = [];
  nodes.forEach((n) => drawShape(n, obstacles));
  const points = nodes.filter((n) => !["block", "junction"].includes(n.type));
  layoutLabels(points, obstacles);
}

function drawShape(n, obstacles) {
  const g = layers.nodes;
  if (n.type === "block") {
    g.appendChild(rect(n.x - 7, n.y - 4.5, 14, 9, "m-block"));
    g.appendChild(text(n.x, n.y + 1.3, n.block || "", "m-block-label"));
    obstacles.push(box(n.x - 7, n.y - 4.5, 14, 9));
  } else if (n.type === "ground") {
    g.appendChild(rect(n.x - 6.5, n.y - 3.5, 13, 7, "m-ground"));
    obstacles.push(box(n.x - 6.5, n.y - 3.5, 13, 7));
  } else if (n.type === "junction") {
    g.appendChild(circle(n.x, n.y, 1.1, "m-node"));
  } else {
    g.appendChild(circle(n.x, n.y, n.type === "gate" ? 2.3 : 1.7, "m-node"));
  }
}

// Shorter display names for the busiest map labels. The searchable names stay full —
// this is only what gets drawn, and short labels collide far less.
const MAPLABEL = {
  "electricity substation": "Substation", "bus / vehicle parking": "Bus Parking",
  "security checkpoint": "Security", "visitor parking": "Visitor Parking",
  "student parking": "Student Parking", "basketball court": "Basketball",
  "cricket ground": "Cricket", "football ground": "Football",
  "football ground (north)": "Football N", "central courtyard": "Courtyard",
  "chinese outlet": "Chinese", "nescafe outlet": "Nescafe",
};
// check the full name first: shortName() would strip "(North)" off Football Ground (North)
// and collapse both football grounds to the same label.
function mapLabel(name) {
  const full = MAPLABEL[name.toLowerCase()];
  if (full) return full;
  const s = shortName(name);
  return MAPLABEL[s.toLowerCase()] || s;
}

// Greedy label placement: prefer the side away from centre, then step further out,
// then flip sides. A label that still cannot clear everything is dropped — an unlabelled
// dot reads better than two names printed on top of each other.
function layoutLabels(points, obstacles) {
  const placed = [...obstacles];
  const OFFS = [0, 2.6, -2.6, 5.2, -5.2, 7.8, -7.8, 10.4, -10.4, 13, -13];
  const GAPS = [3, 5.5, 8];                      // distance from the dot to the label
  points.sort((a, b) => a.y - b.y || a.x - b.x);
  for (const n of points) {
    const s = mapLabel(n.name);
    const w = s.length * 1.75 + 2.5, h = 3.8;    // rough advance width at 3.1px
    const sides = n.x > CENTER_X ? [true, false] : [false, true]; // [preferred, flipped]
    let chosen = null;
    for (const gap of GAPS) {
      for (const left of sides) {
        const lx = left ? n.x - gap : n.x + gap;
        for (const off of OFFS) {
          const b = box(left ? lx - w : lx, n.y - h / 2 + off, w, h);
          if (!inside(b)) continue;              // would run off the edge of the map
          if (!placed.some((p) => hit(b, p))) { chosen = { left, lx, off, b }; break; }
        }
        if (chosen) break;
      }
      if (chosen) break;
    }
    // last resort before dropping the name: stack it centred above or below the dot
    if (!chosen) {
      for (const dy of [-4.6, 4.6, -7.4, 7.4]) {
        const b = box(n.x - w / 2, n.y - h / 2 + dy, w, h);
        if (inside(b) && !placed.some((p) => hit(b, p))) {
          chosen = { center: true, lx: n.x, off: dy, b };
          break;
        }
      }
    }
    if (!chosen) continue;                        // no room — leave this one unlabelled
    placed.push(chosen.b);
    const t = text(chosen.lx, n.y + 1 + chosen.off, s, "m-label");
    t.setAttribute("text-anchor", chosen.center ? "middle" : chosen.left ? "end" : "start");
    layers.labels.appendChild(t);
    if (!chosen.center && Math.abs(chosen.off) > 2.5)  // leader when pushed away
      layers.labels.appendChild(line(n.x, n.y, chosen.lx, n.y + chosen.off, "m-leader"));
  }
}

// ---- route overlay -------------------------------------------------------
function drawRoute(path) {
  layers.route.replaceChildren();
  layers.pins.replaceChildren();
  const pts = path.filter((id) => outdoor[id]).map((id) => outdoor[id]);
  if (pts.length >= 2) {
    const d = "M" + pts.map((p) => `${p.x} ${p.y}`).join(" L ");
    layers.route.appendChild(attr(el("path"), { d, class: "r-line", "marker-mid": "url(#arrow)" }));
  }
  if (pts.length) {
    pin(pts[0], "start");
    pin(pts[pts.length - 1], "end");
  }
}

// A ring wide enough to encircle a block letter rather than sit on top of it. No centre
// dot for the same reason. Direction comes from the arrows along the route line.
function pin(p, which) {
  layers.pins.appendChild(circle(p.x, p.y, 4.2, `r-ring r-ring-${which}`));
}

function ensureDefs(svg) {
  const defs = el("defs");
  // markerUnits defaults to strokeWidth, so the drawn size is markerWidth x the 2.4-unit
  // route stroke — 1.4 keeps the chevron just wider than the band it sits on.
  const m = attr(el("marker"), {
    id: "arrow", viewBox: "0 0 10 10", refX: 5, refY: 5,
    markerWidth: 1.4, markerHeight: 1.4, orient: "auto-start-reverse",
  });
  m.appendChild(attr(el("path"), { d: "M1 1 L9 5 L1 9", class: "arrowhead" }));
  defs.appendChild(m);
  svg.appendChild(defs);
}

// ---- tiny SVG helpers ----------------------------------------------------
function el(tag) { return document.createElementNS(SVGNS, tag); }
function attr(n, a) { for (const k in a) n.setAttribute(k, a[k]); return n; }
function line(x1, y1, x2, y2, cls) { return attr(el("line"), { x1, y1, x2, y2, class: cls }); }
function rect(x, y, w, h, cls) { return attr(el("rect"), { x, y, width: w, height: h, rx: 1.6, class: cls }); }
function circle(cx, cy, r, cls) { return attr(el("circle"), { cx, cy, r, class: cls }); }
function text(x, y, s, cls) { const t = attr(el("text"), { x, y, class: cls }); t.textContent = s; return t; }
function box(x, y, w, h) { return { x, y, w, h }; }
function hit(a, b) { return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y; }
function inside(b) {
  return !VB || (b.x >= VB[0] && b.y >= VB[1] &&
                 b.x + b.w <= VB[0] + VB[2] && b.y + b.h <= VB[1] + VB[3]);
}
function shortName(s) { return s.replace(/ \(.*\)$/, ""); }

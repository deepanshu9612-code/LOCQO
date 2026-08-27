const $ = (id) => document.getElementById(id);
let locations = [], me = null, editing = null;

async function api(path, data) {
  const r = await fetch(path, data ? {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  } : {});
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || `Request failed (${r.status})`);
  return body;
}

function say(text, bad = false) {
  toast(text, bad ? "bad" : "ok");     // ui.js — visible wherever you're scrolled
}

/** Show something in a container while its fetch is in flight. */
function loading(id) {
  const p = document.createElement("p");
  p.className = "empty";
  p.textContent = "Loading…";
  $(id).replaceChildren(p);
}

// ---- DOM helpers. Everything user-authored goes in via textContent, never innerHTML.
function td(text) { const d = document.createElement("td"); d.textContent = text ?? ""; return d; }
function tdEl(...els) { const d = document.createElement("td"); d.className = "row-actions"; d.append(...els); return d; }
function btn(label, cls, onclick) {
  const b = document.createElement("button");
  b.type = "button"; b.className = cls; b.textContent = label;
  b.addEventListener("click", onclick);
  return b;
}
function table(headers, rows) {
  const t = document.createElement("table");
  t.className = "grid";
  const hr = t.createTHead().insertRow();
  headers.forEach((h) => { const th = document.createElement("th"); th.textContent = h; hr.appendChild(th); });
  const tb = t.createTBody();
  rows.forEach((cells) => {
    const tr = tb.insertRow();
    cells.forEach((c) => tr.appendChild(c instanceof HTMLTableCellElement ? c : td(c)));
  });
  return t;
}
function put(id, node) { $(id).replaceChildren(node); }

// ---- boot ----------------------------------------------------------------
boot();
async function boot() {
  const r = await fetch("/api/me");
  if (!r.ok) return location.replace("/login");
  me = await r.json();
  if (me.role !== "admin") return location.replace("/");
  $("who").textContent = `${me.name} · Admin`;
  DAYS.forEach((d, i) => {
    const o = document.createElement("option");
    o.value = i; o.textContent = d;
    $("slot-day").appendChild(o);
  });
  refreshBadges();
  // last, so the day list and the admin check are in place before a tab loads.
  // tabRouter keeps the open tab in the URL, so reload and Back land where you were.
  tabRouter((name) => LOAD[name]().catch((e) => say(e.message, true)), "locations");
}

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

// counts on the Lost & found and SOS tabs, so a waiting queue is visible without clicking
async function refreshBadges() {
  try {
    const s = await api("/api/admin/stats");
    for (const [id, n, ] of [["lost-badge", s.pending_items], ["sos-badge", s.open_sos]]) {
      const b = $(id);
      b.textContent = n;
      b.hidden = !n;
    }
  } catch { /* badges are decoration; a failure here must not break the console */ }
}

$("logout").addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
  location.replace("/login");
});

const LOAD = { locations: loadLocations, paths: loadPaths, users: loadUsers,
               timetable: loadTimetable, notices: loadNotices, lost: loadLost,
               sos: loadSos, stats: loadStats };


// ---- locations -----------------------------------------------------------
async function loadLocations() {
  loading("loc-table");
  locations = await api("/api/admin/locations");
  $("loc-count").textContent = `(${locations.length})`;
  put("loc-table", table(
    ["Id", "Name", "Type", "Level", "Room", "X, Y", ""],
    locations.map((l) => [
      l.id, l.name, l.type, l.level, l.room || "—", `${l.x}, ${l.y}`,
      tdEl(btn("Edit", "mini", () => editLocation(l)),
           btn("Delete", "mini danger", () => removeLocation(l))),
    ])));
  fillEdgeSelects();
}

function editLocation(l) {
  editing = l.id;
  $("loc-id").value = l.id;
  $("loc-id").readOnly = true;          // the id is the graph's key — renaming would orphan paths
  $("loc-name").value = l.name;
  $("loc-type").value = l.type;
  $("loc-level").value = l.level;
  $("loc-room").value = l.room || "";
  $("loc-scene").value = l.tour_scene || "";
  $("loc-x").value = l.x;
  $("loc-y").value = l.y;
  try { $("loc-aliases").value = JSON.parse(l.aliases || "[]").join(", "); }
  catch { $("loc-aliases").value = ""; }
  $("loc-submit").textContent = "Save changes";
  $("loc-reset").hidden = false;
  $("loc-form").scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetLocForm() {
  editing = null;
  $("loc-form").reset();
  $("loc-id").readOnly = false;
  $("loc-submit").textContent = "Add location";
  $("loc-reset").hidden = true;
}
$("loc-reset").addEventListener("click", resetLocForm);

$("loc-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    id: $("loc-id").value, name: $("loc-name").value, type: $("loc-type").value,
    level: $("loc-level").value, room: $("loc-room").value,
    tour_scene: $("loc-scene").value, x: $("loc-x").value, y: $("loc-y").value,
    aliases: $("loc-aliases").value,
  };
  try {
    await api(editing ? "/api/admin/locations/update" : "/api/admin/locations", payload);
    say(editing ? `Saved ${payload.id}.` : `Added ${payload.id}.`);
    resetLocForm();
    await loadLocations();
  } catch (err) { say(err.message, true); }
});

async function removeLocation(l) {
  if (!await confirmAction(
      `Delete "${l.name}"? Every path connected to it is removed too.`)) return;
  try {
    const r = await api("/api/admin/locations/delete", { id: l.id });
    say(`Deleted ${r.deleted} — ${r.paths_removed} path(s) removed with it.`);
    if (editing === l.id) resetLocForm();
    await loadLocations();
  } catch (err) { say(err.message, true); }
}

// ---- paths ---------------------------------------------------------------
function fillEdgeSelects() {
  [$("edge-a"), $("edge-b")].forEach((sel) => {
    const keep = sel.value;
    sel.replaceChildren();
    locations.forEach((l) => {
      const o = document.createElement("option");
      o.value = l.id;
      o.textContent = `${l.name} — ${l.id}`;
      sel.appendChild(o);
    });
    if (keep) sel.value = keep;
  });
}

async function loadPaths() {
  loading("edge-table");
  if (!locations.length) locations = await api("/api/admin/locations");
  fillEdgeSelects();
  const edges = await api("/api/admin/edges");
  $("edge-count").textContent = `(${edges.length})`;
  put("edge-table", table(["From", "To", "Type", "Weight", ""], edges.map((e) => [
    e.a_name, e.b_name, e.kind, String(e.weight),
    tdEl(btn("Delete", "mini danger", () => removeEdge(e))),
  ])));
}

async function removeEdge(e) {
  if (!await confirmAction(`Remove the path ${e.a_name} → ${e.b_name}?`, "Remove")) return;
  try {
    await api("/api/admin/edges/delete", { a: e.a, b: e.b });
    say("Path removed.");
    await loadPaths();
  } catch (err) { say(err.message, true); }
}

$("edge-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const w = $("edge-weight").value.trim();
  try {
    await api("/api/admin/edges", {
      a: $("edge-a").value, b: $("edge-b").value,
      kind: $("edge-kind").value, weight: w === "" ? null : w,
    });
    say("Path added.");
    $("edge-weight").value = "";
    await loadPaths();
  } catch (err) { say(err.message, true); }
});

// ---- users ---------------------------------------------------------------
async function loadUsers() {
  loading("user-table");
  const users = await api("/api/admin/users");
  $("user-count").textContent = `(${users.length})`;
  put("user-table", table(["Username", "Name", "Role", "Status", ""], users.map((u) => [
    u.username, u.name, u.role, u.active ? "active" : "disabled",
    tdEl(
      btn(u.role === "admin" ? "Make student" : "Make admin", "mini",
          () => updateUser({ id: u.id, role: u.role === "admin" ? "student" : "admin" })),
      btn(u.active ? "Disable" : "Enable", "mini",
          () => updateUser({ id: u.id, active: u.active ? 0 : 1 })),
      btn("Reset password", "mini", async () => {
        const p = await promptAction(`New password for ${u.username}`, {
          type: "password", label: "Set password", minLength: 8,
          autocomplete: "new-password", hint: "At least 8 characters",
        });
        if (p) updateUser({ id: u.id, password: p });
      }),
    ),
  ])));
}

async function updateUser(patch) {
  try {
    await api("/api/admin/users/update", patch);
    say("User updated.");
    await loadUsers();
  } catch (err) { say(err.message, true); }
}

$("user-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/admin/users", {
      username: $("u-user").value.trim(), name: $("u-name").value.trim(),
      password: $("u-pass").value, role: $("u-role").value,
    });
    say(`Added ${$("u-user").value.trim()}.`);
    $("user-form").reset();
    await loadUsers();
  } catch (err) { say(err.message, true); }
});

// ---- timetable -----------------------------------------------------------
function fillRoomSelects() {
  const rooms = locations.filter((l) => ["lab", "library"].includes(l.type));
  [$("slot-room")].forEach((sel) => {
    const keep = sel.value;
    sel.replaceChildren(...rooms.map((l) => {
      const o = document.createElement("option");
      o.value = l.id; o.textContent = l.name;
      return o;
    }));
    if (keep) sel.value = keep;
  });
  const venue = $("notice-venue");
  const keep = venue.value;
  venue.replaceChildren(...[{ id: "", name: "No venue" }].concat(locations).map((l) => {
    const o = document.createElement("option");
    o.value = l.id; o.textContent = l.name;
    return o;
  }));
  if (keep) venue.value = keep;
}

async function loadTimetable() {
  loading("slot-table");
  if (!locations.length) locations = await api("/api/admin/locations");
  fillRoomSelects();
  const slots = await api("/api/admin/timetable");
  $("slot-count").textContent = `(${slots.length})`;
  put("slot-table", table(["Day", "Room", "Time", "What's on", ""], slots.length
    ? slots.map((s) => [
        s.day, s.room, `${s.start}–${s.end}`, s.title,
        tdEl(btn("Delete", "mini danger", () => removeSlot(s))),
      ])
    : [["No slots yet — every room reads as free.", "", "", "", td("")]]));
}

async function removeSlot(s) {
  try {
    await api("/api/admin/timetable/delete", { id: s.id });
    say("Slot removed.");
    await loadTimetable();
  } catch (err) { say(err.message, true); }
}

$("slot-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/admin/timetable", {
      location_id: $("slot-room").value, weekday: $("slot-day").value,
      start: $("slot-start").value, end: $("slot-end").value, title: $("slot-title").value,
    });
    say("Slot added.");
    $("slot-title").value = "";
    await loadTimetable();
  } catch (err) { say(err.message, true); }
});

// ---- lost & found moderation ---------------------------------------------
async function loadLost() {
  loading("lost-table");
  const items = await api("/api/admin/lost-found");
  put("lost-table", table(["Item", "Type", "Where", "Posted by", "Status", ""],
    items.length ? items.map((it) => [
      it.title, it.kind, it.place || "—", it.posted_by || "—", it.status,
      tdEl(
        ...(it.status === "pending"
          ? [btn("Approve", "mini", () => moderate(it, "approved")),
             btn("Reject", "mini danger", () => moderate(it, "rejected"))]
          : [btn("Resolve", "mini", () => moderate(it, "resolved"))]),
        btn("Delete", "mini danger", () => removeItem(it)),
      ),
    ]) : [["Nothing reported yet.", "", "", "", "", td("")]]));
  refreshBadges();
}

async function moderate(item, status) {
  try {
    await api("/api/admin/lost-found/moderate", { id: item.id, status });
    say(`Item ${status}.`);
    await loadLost();
  } catch (err) { say(err.message, true); }
}

async function removeItem(item) {
  if (!await confirmAction(`Delete "${item.title}" permanently?`)) return;
  try {
    await api("/api/admin/lost-found/delete", { id: item.id });
    say("Item deleted.");
    await loadLost();
  } catch (err) { say(err.message, true); }
}

// ---- SOS -----------------------------------------------------------------
async function loadSos() {
  loading("sos-table");
  const alerts = await api("/api/admin/sos");
  put("sos-table", table(["Raised", "Who", "Where", "What", "Status", ""],
    alerts.length ? alerts.map((a) => [
      (a.created_at || "").slice(0, 16).replace("T", " "),
      a.raised_by || "—", a.place || "not stated", a.note || "—", a.status,
      tdEl(...(a.status === "open"
        ? [btn("Acknowledge", "mini", () => updateSos(a, "acknowledged")),
           btn("Close", "mini danger", () => updateSos(a, "closed"))]
        : a.status === "acknowledged"
          ? [btn("Close", "mini danger", () => updateSos(a, "closed"))]
          : [td("")])),
    ]) : [["No alerts raised.", "", "", "", "", td("")]]));
  refreshBadges();
}

async function updateSos(alert, status) {
  try {
    await api("/api/admin/sos/update", { id: alert.id, status });
    say(`Alert ${status}.`);
    await loadSos();
  } catch (err) { say(err.message, true); }
}

// ---- announcements -------------------------------------------------------
async function loadNotices() {
  loading("notice-table");
  if (!locations.length) locations = await api("/api/admin/locations");
  fillRoomSelects();
  const list = await api("/api/admin/announcements");
  put("notice-table", table(["Message", "When", "Venue", "Posted", ""], list.length
    ? list.map((n) => [
        n.body, n.starts_at ? n.starts_at.replace("T", " ") : "standing notice",
        n.venue || "—", (n.created_at || "").slice(0, 16).replace("T", " "),
        tdEl(btn("Delete", "mini danger", () => removeNotice(n))),
      ])
    : [["Nothing posted yet.", "", "", "", td("")]]));
}

async function removeNotice(n) {
  try {
    await api("/api/admin/announcements/delete", { id: n.id });
    say("Announcement deleted.");
    await loadNotices();
  } catch (err) { say(err.message, true); }
}

$("notice-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/admin/announcements", {
      body: $("notice-body").value,
      starts_at: $("notice-when").value,       // blank -> standing notice
      location_id: $("notice-venue").value,
    });
    say("Posted — students will see it on the navigator.");
    $("notice-form").reset();
    await loadNotices();
  } catch (err) { say(err.message, true); }
});

// ---- analytics -----------------------------------------------------------
async function loadStats() {
  const s = await api("/api/admin/stats");
  const tiles = [["Route lookups", s.total_lookups], ["Students", s.students],
                 ["Locations", s.locations], ["Paths", s.paths]].map(([label, n]) => {
    const d = document.createElement("div");
    d.className = "tile";
    const v = document.createElement("b"); v.textContent = n;
    const l = document.createElement("span"); l.textContent = label;
    d.append(v, l);
    return d;
  });
  $("stat-tiles").replaceChildren(...tiles);

  const rank = (rows) => table(["Place", "Lookups"],
    rows.length ? rows.map((r) => [r.name, String(r.n)]) : [["No lookups yet", "0"]]);
  put("stat-to", rank(s.top_destinations));
  put("stat-from", rank(s.top_starts));
}

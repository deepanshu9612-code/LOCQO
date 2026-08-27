const $ = (id) => document.getElementById(id);
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
let me = null, locations = [];

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
  toast(text, bad ? "bad" : "ok");     // ui.js
}

function loading(id) {
  const p = document.createElement("p");
  p.className = "empty";
  p.textContent = "Loading…";
  $(id).replaceChildren(p);
}

// user-authored text always goes in as textContent, never innerHTML
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}
function card(...kids) { const c = el("div", "card"); c.append(...kids); return c; }
function empty(text) { return el("p", "empty", text); }

// ---- boot ----------------------------------------------------------------
boot();
async function boot() {
  const r = await fetch("/api/me");
  if (!r.ok) return location.replace("/login");
  me = await r.json();
  $("who").textContent = `${me.name} · ${me.role === "admin" ? "Admin" : "Student"}`;
  if (me.role === "admin") $("adminlink").hidden = false;

  DAYS.forEach((d, i) => {
    const o = document.createElement("option");
    o.value = i; o.textContent = d;
    $("when-day").appendChild(o);
  });
  setNow();

  locations = await api("/api/locations");
  [$("lf-place")].forEach((sel) => {
    sel.replaceChildren(...[{ id: "", name: "Not sure" }].concat(locations).map((l) => {
      const o = document.createElement("option");
      o.value = l.id; o.textContent = l.name;
      return o;
    }));
  });

  // last: loadRooms reads #when-time, which setNow() above has just filled
  tabRouter((name) => LOAD[name]().catch((e) => say(e.message, true)), "rooms");
}

$("logout").addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
  location.replace("/login");
});

const LOAD = { rooms: loadRooms, notices: loadNotices, lost: loadLost };

// ---- free rooms ----------------------------------------------------------
function setNow() {
  const now = new Date();
  $("when-day").value = (now.getDay() + 6) % 7;          // JS Sunday=0 -> Monday=0
  $("when-time").value =
    `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
}
$("when-now").addEventListener("click", () => { setNow(); loadRooms(); });
$("when-day").addEventListener("change", loadRooms);
$("when-time").addEventListener("change", loadRooms);

async function loadRooms() {
  loading("rooms-list");
  const [h, m] = ($("when-time").value || "09:00").split(":").map(Number);
  const data = await api(`/api/free-rooms?day=${$("when-day").value}&time=${h * 60 + m}`);
  const free = data.rooms.filter((r) => r.free);
  const busy = data.rooms.filter((r) => !r.free);

  $("rooms-caption").textContent = data.has_timetable
    ? `${free.length} of ${data.rooms.length} rooms free on ${data.day} at ${data.time}.`
    : "No timetable has been entered yet, so every room shows as free. "
      + "An admin can add class times under Admin → Timetable.";

  const list = $("rooms-list");
  list.replaceChildren();
  if (!data.rooms.length) { list.append(empty("No rooms on record yet.")); return; }

  // Grouped, because the question is "which are free" — not "here are all 20 rooms".
  // A free room with nothing scheduled says nothing further; silence is the good news.
  const group = (label, rooms) => {
    if (!rooms.length) return;
    list.append(el("h3", "group-h", `${label} · ${rooms.length}`));
    const grid = el("div", "cards");
    rooms.forEach((r) => {
      const c = card();
      c.classList.add(r.free ? "is-free" : "is-busy");
      const top = el("div", "card-top");
      top.append(el("b", null, r.name),
                 el("span", `pill ${r.free ? "pill-free" : "pill-busy"}`,
                    r.free ? "Free" : "In use"));
      c.append(top);
      if (r.room) c.append(el("span", "card-meta", `Room ${r.room}`));
      if (!r.free) c.append(el("span", "card-note", `${r.what} until ${r.until}`));
      else if (r.until) c.append(el("span", "card-note", `Free until ${r.until}`));
      const go = el("a", "card-link", "Directions →");
      go.href = `/?to=${encodeURIComponent(r.id)}`;
      c.append(go);
      grid.append(c);
    });
    list.append(grid);
  };
  group("Free now", free);
  group("In use", busy);
}

// ---- notices & events ----------------------------------------------------
async function loadNotices() {
  loading("events-list");
  const all = await api("/api/announcements");
  const events = all.filter((n) => n.starts_at).sort((a, b) => a.starts_at.localeCompare(b.starts_at));
  const notices = all.filter((n) => !n.starts_at);

  const ev = $("events-list");
  ev.replaceChildren();
  if (!events.length) ev.append(empty("Nothing scheduled right now."));
  events.forEach((n) => {
    const c = card(el("span", "card-when", n.starts_at.replace("T", " ")), el("p", "card-body", n.body));
    if (n.venue) {
      const go = el("a", "linkbtn", `Directions to ${n.venue}`);
      go.href = `/?to=${encodeURIComponent(n.location_id)}`;
      c.append(go);
    }
    ev.append(c);
  });

  const nt = $("notices-list");
  nt.replaceChildren();
  if (!notices.length) nt.append(empty("No notices right now."));
  notices.forEach((n) => nt.append(card(el("p", "card-body", n.body))));
}

// ---- lost & found --------------------------------------------------------
async function loadLost() {
  loading("lost-list");
  const items = await api("/api/lost-found");
  const list = $("lost-list");
  list.replaceChildren();
  if (!items.length) { list.append(empty("Nothing posted yet. Be the first.")); return; }
  items.forEach((it) => {
    const c = card();
    const top = el("div", "card-top");
    top.append(el("b", null, it.title),
               el("span", `pill pill-${it.kind}`, it.kind === "lost" ? "Lost" : "Found"));
    c.append(top);
    if (it.status !== "approved") c.append(el("span", `pill pill-${it.status}`, it.status));
    if (it.place) c.append(el("span", "card-meta", it.place));
    if (it.details) c.append(el("p", "card-body", it.details));
    if (it.contact) c.append(el("span", "card-note", `Contact: ${it.contact}`));
    c.append(el("span", "card-note", `Posted by ${it.posted_by || "someone"}`));
    if (it.user_id === undefined || it.status === "approved") {
      const mine = it.posted_by && me && it.posted_by === me.name;
      if (mine) {
        const done = el("button", "mini", "Mark resolved");
        done.type = "button";
        done.addEventListener("click", async () => {
          try {
            await api("/api/lost-found/resolve", { id: it.id });
            say("Marked as resolved.");
            await loadLost();
          } catch (e) { say(e.message, true); }
        });
        c.append(done);
      }
    }
    list.append(c);
  });
}

$("lost-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/lost-found", {
      kind: $("lf-kind").value, title: $("lf-title").value,
      details: $("lf-details").value, location_id: $("lf-place").value,
      contact: $("lf-contact").value,
    });
    say("Posted — an admin will review it before it appears.");
    $("lost-form").reset();
    await loadLost();
  } catch (err) { say(err.message, true); }
});

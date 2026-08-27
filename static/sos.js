/* Emergency button + dialog, shared by the navigator and the campus hub.
   Built in JS so the markup lives in exactly one place.

   It is deliberately a large, high-contrast button labelled with the word SOS rather
   than an icon, fixed within thumb reach. It raises an in-app alert to admins and
   lists numbers to dial — it cannot place a call, and it says so. */
(function () {
  const NS = "http://www.w3.org/2000/svg";
  let dialog, statusEl, sendBtn, placeSel, noteEl, contactsEl;

  const bar = document.createElement("button");
  bar.type = "button";
  bar.id = "sos-open";
  bar.className = "sos-fab";
  bar.textContent = "SOS";
  bar.setAttribute("aria-label", "Emergency help and campus numbers");
  bar.addEventListener("click", open);
  document.body.appendChild(bar);

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function build() {
    dialog = document.createElement("dialog");
    dialog.id = "sos-dialog";
    dialog.className = "sos-dialog";
    dialog.setAttribute("aria-labelledby", "sos-h");

    const h = el("h2", "sos-h", "Emergency");
    h.id = "sos-h";

    const warn = el("p", "sos-warn");
    warn.append(
      el("strong", null, "This does not call emergency services."),
      document.createTextNode(
        " Dial a number below yourself. Sending an alert notifies campus admins in this app only."));

    contactsEl = el("ul", "sos-numbers");

    const label = el("label", "field");
    label.append(el("span", "field-label", "Where are you?"));
    placeSel = document.createElement("select");
    placeSel.id = "sos-place";
    label.append(placeSel);

    const noteLabel = el("label", "field");
    noteLabel.append(el("span", "field-label", "What's happening? (optional)"));
    noteEl = document.createElement("input");
    noteEl.id = "sos-note";
    noteEl.maxLength = 200;
    noteEl.placeholder = "e.g. someone fainted near the canteen";
    noteLabel.append(noteEl);

    sendBtn = el("button", "sos-send", "Alert campus admins");
    sendBtn.type = "button";
    sendBtn.id = "sos-send";
    sendBtn.addEventListener("click", send);

    statusEl = el("p", "sos-status");
    statusEl.id = "sos-status";
    statusEl.setAttribute("role", "status");
    statusEl.setAttribute("aria-live", "assertive");

    const route = el("a", "linkbtn", "Directions to Security");
    route.id = "sos-route";
    route.href = "/?to=security";

    const close = el("button", "linkbtn", "Close");
    close.type = "button";
    close.id = "sos-close";
    close.setAttribute("aria-label", "Close emergency panel");
    close.addEventListener("click", () => dialog.close());

    const actions = el("div", "sos-actions");
    actions.append(route, close);
    dialog.append(h, warn, contactsEl, label, noteLabel, sendBtn, statusEl, actions);
    document.body.appendChild(dialog);
  }

  async function open() {
    if (!dialog) build();
    statusEl.textContent = "";
    statusEl.className = "sos-status";
    sendBtn.disabled = false;
    sendBtn.textContent = "Alert campus admins";
    try {
      const [info, locs] = await Promise.all([
        fetch("/api/emergency").then((r) => r.json()),
        fetch("/api/locations").then((r) => r.json()),
      ]);
      contactsEl.replaceChildren(...info.contacts.map((c) => {
        const li = el("li");
        li.append(el("span", "sos-num-label", c.label));
        if (c.number) {
          const a = el("a", "sos-num", c.number);
          a.href = `tel:${c.number.replace(/\s/g, "")}`;
          li.append(a);
        } else {
          li.append(el("span", "sos-num sos-num-unset", "not set"));
        }
        return li;
      }));
      placeSel.replaceChildren(...[{ id: "", name: "I'm not sure" }].concat(locs).map((l) => {
        const o = document.createElement("option");
        o.value = l.id;
        o.textContent = l.name;
        return o;
      }));
    } catch {
      statusEl.textContent = "Couldn't load emergency details. The numbers above still apply.";
    }
    dialog.showModal();
  }

  async function send() {
    sendBtn.disabled = true;
    sendBtn.textContent = "Sending…";
    statusEl.className = "sos-status";
    statusEl.textContent = "Sending your alert…";
    try {
      const r = await fetch("/api/sos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ location_id: placeSel.value, note: noteEl.value }),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(body.error || "Alert failed");
      statusEl.className = "sos-status sent";
      statusEl.textContent = "Alert sent to campus admins. Keep dialling if this is urgent.";
      sendBtn.textContent = "Alert sent";
    } catch (e) {
      statusEl.className = "sos-status failed";
      statusEl.textContent = `Alert did not send (${e.message}). Dial a number above.`;
      sendBtn.disabled = false;
      sendBtn.textContent = "Try again";
    }
  }
})();

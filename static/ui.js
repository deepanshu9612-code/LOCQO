/* Shared UI primitives: toasts, and dialog-based confirm/prompt.

   Toasts, because a message pinned to the top of the page is invisible the moment you
   act on row 40 of a table. Dialogs instead of native confirm()/prompt(), because those
   can't be styled, can't be given our own copy, and some browsers let users suppress
   them entirely — losing the action. <dialog> gives focus trapping and Esc for free. */
(function () {
  let host;

  function ensureHost() {
    if (!host) {
      host = document.createElement("div");
      host.className = "toasts";
      host.setAttribute("role", "status");
      host.setAttribute("aria-live", "polite");
      document.body.appendChild(host);
    }
    return host;
  }

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  /** toast("Saved.")  |  toast("That failed", "bad") */
  window.toast = function (text, kind = "ok") {
    if (!text) return;
    const t = el("div", `toast toast-${kind}`, text);
    ensureHost().appendChild(t);
    // failures linger — you may need to read them twice
    const life = kind === "bad" ? 6000 : 3500;
    setTimeout(() => {
      t.classList.add("out");
      setTimeout(() => t.remove(), 250);
    }, life);
  };

  function modal(build) {
    return new Promise((resolve) => {
      const d = document.createElement("dialog");
      d.className = "ask";
      let settled = false;
      const done = (value) => {
        if (settled) return;
        settled = true;
        resolve(value);
        d.close();
      };
      d.addEventListener("cancel", () => done(null));       // Esc
      d.addEventListener("close", () => { done(null); d.remove(); });
      build(d, done);
      document.body.appendChild(d);
      d.showModal();
    });
  }

  /** await confirmAction("Delete X?")  ->  true / false */
  window.confirmAction = function (message, confirmLabel = "Delete") {
    return modal((d, done) => {
      const row = el("div", "ask-actions");
      const no = el("button", "linkbtn", "Cancel");
      // every confirm we raise is destructive — it must never look like the safe default
      const yes = el("button", "ask-go ask-danger", confirmLabel);
      no.type = yes.type = "button";
      no.addEventListener("click", () => done(false));
      yes.addEventListener("click", () => done(true));
      row.append(no, yes);
      d.append(el("p", "ask-body", message), row);
      queueMicrotask(() => yes.focus());
    }).then((v) => v === true);
  };

  /** await promptAction("New password", {type:"password"})  ->  string / null */
  window.promptAction = function (message, opts = {}) {
    return modal((d, done) => {
      const form = document.createElement("form");
      form.className = "ask-form";
      const label = el("label", "field");
      label.append(el("span", "field-label", message));
      const input = document.createElement("input");
      input.type = opts.type || "text";
      if (opts.placeholder) input.placeholder = opts.placeholder;
      if (opts.minLength) input.minLength = opts.minLength;
      if (opts.autocomplete) input.autocomplete = opts.autocomplete;
      label.append(input);
      if (opts.hint) label.append(el("span", "hint", opts.hint));

      const row = el("div", "ask-actions");
      const no = el("button", "linkbtn", "Cancel");
      no.type = "button";
      const yes = el("button", "ask-go", opts.label || "Save");
      yes.type = "submit";
      no.addEventListener("click", () => done(null));
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        done(input.value || null);
      });
      row.append(no, yes);
      form.append(label, row);
      d.append(form);
      queueMicrotask(() => input.focus());
    });
  };

  /** Remembers which tab you were on across reload, back and shared links. */
  window.tabRouter = function (onChange, fallback) {
    const nav = (name, push) => {
      const tab = document.querySelector(`.tab[data-tab="${name}"]`);
      if (!tab) return false;
      document.querySelectorAll(".tab").forEach((x) => {
        const on = x === tab;
        x.classList.toggle("is-on", on);
        x.setAttribute("aria-selected", String(on));
      });
      document.querySelectorAll(".tabpane").forEach((p) => (p.hidden = p.id !== "pane-" + name));
      if (push) history.replaceState(null, "", "#" + name);
      onChange(name);
      return true;
    };
    document.querySelectorAll(".tab").forEach((b) =>
      b.addEventListener("click", () => nav(b.dataset.tab, true)));
    addEventListener("hashchange", () => nav(location.hash.slice(1), false));
    if (!nav(location.hash.slice(1), false)) nav(fallback, false);
  };
})();

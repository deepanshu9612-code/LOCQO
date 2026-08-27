const $ = (id) => document.getElementById(id);

// already signed in? don't make them do it twice.
fetch("/api/me").then((r) => { if (r.ok) location.replace("/"); });

function show(signup) {
  $("signup").hidden = !signup;
  $("signin").hidden = signup;
  $("tab-signup").classList.toggle("is-on", signup);
  $("tab-signin").classList.toggle("is-on", !signup);
  $("tab-signup").setAttribute("aria-selected", String(signup));
  $("tab-signin").setAttribute("aria-selected", String(!signup));
  $("msg").textContent = "";
  ($(signup ? "su-name" : "si-user")).focus();
}
$("tab-signin").addEventListener("click", () => show(false));
$("tab-signup").addEventListener("click", () => show(true));

async function submit(form, url, data) {
  const btn = form.querySelector("button[type=submit]");
  const label = btn.textContent;
  btn.disabled = true; btn.textContent = "Just a moment…";
  $("msg").textContent = "";
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) { $("msg").textContent = body.error || "That didn’t work. Try again."; return; }
    location.replace("/");
  } catch {
    $("msg").textContent = "Couldn’t reach the server. Is it running?";
  } finally {
    btn.disabled = false; btn.textContent = label;
  }
}

$("signin").addEventListener("submit", (e) => {
  e.preventDefault();
  submit(e.target, "/api/login", {
    username: $("si-user").value.trim(),
    password: $("si-pass").value,
  });
});

$("signup").addEventListener("submit", (e) => {
  e.preventDefault();
  submit(e.target, "/api/signup", {
    name: $("su-name").value.trim(),
    username: $("su-user").value.trim(),
    password: $("su-pass").value,
  });
});

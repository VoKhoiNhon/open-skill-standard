"""One self-contained HTML page for the skill graph: inline CSS and JS, no network."""

import json

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Skill graph</title>
<style>
:root {
  --bg: #ffffff; --fg: #1a1a1a; --muted: #555555; --line: #c8c8c8; --card: #f4f4f4;
  --accent: #0b57d0; --ok: #1e6b34; --off: #8a3b00; --focus: #0b57d0;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #121212; --fg: #e8e8e8; --muted: #b0b0b0; --line: #4a4a4a; --card: #1e1e1e;
    --accent: #8ab4f8; --ok: #7ee2a0; --off: #ffb77a; --focus: #8ab4f8;
  }
}
* { box-sizing: border-box; }
body { margin: 0; font: 15px/1.45 system-ui, sans-serif; background: var(--bg); color: var(--fg); }
header, main { padding: 0 16px; }
h1 { font-size: 1.4rem; margin: 16px 0 4px; }
h2 { font-size: 1.05rem; margin: 0 0 8px; }
.muted { color: var(--muted); }
.board { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin: 16px 0; }
.col { border: 1px solid var(--line); border-radius: 6px; padding: 8px; }
.col ul, .plain { list-style: none; margin: 0; padding: 0; }
.skill { display: block; width: 100%; text-align: left; margin: 0 0 6px; padding: 6px 8px; border: 1px solid var(--line);
  border-radius: 4px; background: var(--card); color: var(--fg); font: inherit; cursor: pointer; }
.skill[aria-pressed="true"] { border-color: var(--accent); box-shadow: inset 3px 0 0 var(--accent); }
.skill small { display: block; color: var(--muted); }
.on { color: var(--ok); } .off { color: var(--off); }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
#detail { border: 1px solid var(--line); border-radius: 6px; padding: 12px; margin: 16px 0; }
#detail dt { font-weight: 600; margin-top: 6px; }
#detail dd { margin: 0; }
.skip { position: absolute; left: -9999px; }
.skip:focus { position: static; }
kbd { border: 1px solid var(--line); border-radius: 3px; padding: 0 4px; }
.link { background: none; border: 0; padding: 0; color: var(--accent); text-decoration: underline; font: inherit; cursor: pointer; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 24px; }
.filters { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; margin: 12px 0; }
.filters label { display: flex; flex-direction: column; font-size: 0.85rem; color: var(--muted); }
input, select, .reset { font: inherit; color: var(--fg); background: var(--bg); border: 1px solid var(--muted); border-radius: 4px; padding: 4px 6px; }
.reset { cursor: pointer; }
th, td { text-align: left; border-bottom: 1px solid var(--line); padding: 4px 8px; vertical-align: top; }
</style>
</head>
<body>
<a class="skip" href="#board">Skip to skills</a>
<header>
<h1>Skill graph</h1>
<p class="muted" id="summary" role="status" aria-live="polite"></p>
<p class="muted">Press <kbd>/</kbd> to search, <kbd>Esc</kbd> to clear the search.</p>
</header>
<main>
<form class="filters" role="search" aria-label="Filter skills" id="filters">
<label for="q">Search <input type="search" id="q" placeholder="name, description, artifact"></label>
<label for="f-role">Role <select id="f-role"><option value="">All roles</option></select></label>
<label for="f-phase">Phase <select id="f-phase"><option value="">All phases</option></select></label>
<label for="f-source">Source <select id="f-source"><option value="">All sources</option></select></label>
<label for="f-installed">Installed <select id="f-installed"><option value="">Installed or not</option>
<option value="yes">Installed only</option><option value="no">Not installed only</option></select></label>
<button type="reset" class="reset">Clear filters</button>
</form>
<noscript><p>This page needs JavaScript to draw the graph. The same data is available with <code>open-skill graph --format json</code>.</p></noscript>
<section aria-labelledby="phases-h">
<h2 id="phases-h">Skills by phase</h2>
<div class="board" id="board" tabindex="-1"></div>
</section>
<section id="detail" aria-labelledby="detail-h" aria-live="polite">
<h2 id="detail-h">Details</h2>
<p class="muted">Choose a skill to see its artifacts, relations and the roles that recommend it.</p>
</section>
<section aria-labelledby="artifacts-h">
<h2 id="artifacts-h">Artifacts</h2>
<table><thead><tr><th scope="col">Artifact</th><th scope="col">Produced by</th><th scope="col">Consumed by</th></tr></thead>
<tbody id="artifacts"></tbody></table>
</section>
<section aria-labelledby="roles-h">
<h2 id="roles-h">Roles</h2>
<p class="muted">Choose a role to show only the skills it recommends.</p>
<ul class="plain" id="roles"></ul>
</section>
</main>
<script type="application/json" id="graph-data">__DATA__</script>
<script>
(function () {
  "use strict";
  var G = JSON.parse(document.getElementById("graph-data").textContent);
  var byId = {}, out = {}, into = {};
  G.nodes.forEach(function (n) { byId[n.id] = n; out[n.id] = []; into[n.id] = []; });
  G.edges.forEach(function (e) {
    (out[e.from] = out[e.from] || []).push(e);
    (into[e.to] = into[e.to] || []).push(e);
  });
  var skills = G.nodes.filter(function (n) { return n.kind !== "phase" && n.kind !== "artifact" && n.kind !== "role"; });
  var phases = G.nodes.filter(function (n) { return n.kind === "phase"; }).map(function (n) { return n.id.slice(6); });
  var roles = G.nodes.filter(function (n) { return n.kind === "role"; });
  var selected = null;

  function el(tag, attrs, text) {
    var x = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { x.setAttribute(k, attrs[k]); });
    if (text != null) x.textContent = text;
    return x;
  }
  function related(id, dir, type) {
    return (dir === "out" ? out[id] : into[id]).filter(function (e) { return e.type === type; })
      .map(function (e) { return dir === "out" ? e.to : e.from; });
  }
  function strip(ref) { return ref.replace(/^(artifact|role|phase):/, ""); }

  function haystack(s) {
    return [s.id, s.description || "", s.source, s.phases.join(" ")]
      .concat(related(s.id, "out", "produces"), related(s.id, "in", "consumes")).join(" ").toLowerCase();
  }
  function value(id) { return document.getElementById(id).value; }
  function visible() {
    var words = value("q").toLowerCase().split(/\s+/).filter(Boolean);
    var role = value("f-role"), phase = value("f-phase"), source = value("f-source"), inst = value("f-installed");
    var recommended = role ? related(role, "out", "recommends") : null;
    return skills.filter(function (s) {
      if (recommended && recommended.indexOf(s.id) < 0) return false;
      if (phase && s.phases.indexOf(phase) < 0) return false;
      if (source && s.source !== source) return false;
      if (inst && s.installed !== (inst === "yes")) return false;
      var text = haystack(s);
      return words.every(function (w) { return text.indexOf(w) >= 0; });
    });
  }
  function fill(id, pairs) {
    var sel = document.getElementById(id);
    pairs.forEach(function (p) { sel.appendChild(el("option", {value: p[0]}, p[1])); });
  }

  function card(s) {
    var b = el("button", {type: "button", "class": "skill", "data-id": s.id, "aria-pressed": String(s.id === selected)});
    b.appendChild(el("span", {}, s.id));
    var meta = el("small");
    meta.appendChild(el("span", {"class": s.installed ? "on" : "off"}, s.installed ? "installed" : "not installed"));
    meta.appendChild(document.createTextNode(" · " + s.source));
    b.appendChild(meta);
    b.addEventListener("click", function () { select(s.id); });
    return b;
  }

  function drawBoard(list) {
    var board = document.getElementById("board");
    board.textContent = "";
    phases.concat(["unphased"]).forEach(function (ph) {
      var members = list.filter(function (s) { return ph === "unphased" ? !s.phases.length : s.phases.indexOf(ph) >= 0; });
      if (!members.length) return;
      var col = el("section", {"class": "col", "aria-label": "Phase " + ph});
      col.appendChild(el("h3", {"class": "muted"}, ph + " (" + members.length + ")"));
      var ul = el("ul");
      members.forEach(function (s) { var li = el("li"); li.appendChild(card(s)); ul.appendChild(li); });
      col.appendChild(ul);
      board.appendChild(col);
    });
  }

  function linkList(dd, ids) {
    if (!ids.length) { dd.textContent = "none"; return; }
    ids.forEach(function (id, i) {
      if (i) dd.appendChild(document.createTextNode(", "));
      if (byId[id] && skills.indexOf(byId[id]) >= 0) {
        var b = el("button", {type: "button", "class": "link"}, id);
        b.addEventListener("click", function () { select(id); });
        dd.appendChild(b);
      } else {
        dd.appendChild(document.createTextNode(strip(id)));
      }
    });
  }

  function drawDetail() {
    var box = document.getElementById("detail");
    var s = byId[selected];
    if (!s) return;
    box.textContent = "";
    box.appendChild(el("h2", {id: "detail-h"}, s.id));
    if (s.description) box.appendChild(el("p", {}, s.description));
    var dl = el("dl");
    function row(label, ids) { dl.appendChild(el("dt", {}, label)); var dd = el("dd"); linkList(dd, ids); dl.appendChild(dd); }
    row("Source", [s.source]);
    row("Installed", [s.installed ? "yes" : "no"]);
    row("Phases", s.phases);
    row("Produces", related(s.id, "out", "produces"));
    row("Consumes", related(s.id, "in", "consumes"));
    row("Requires", related(s.id, "out", "requires"));
    row("Precedes", related(s.id, "out", "precedes"));
    row("Alternatives", related(s.id, "out", "alternative-to"));
    row("Conflicts with", related(s.id, "out", "conflicts-with").concat(related(s.id, "in", "conflicts-with")));
    row("Recommended by", related(s.id, "in", "recommends"));
    box.appendChild(dl);
  }

  function drawArtifacts(list) {
    var ids = {}; list.forEach(function (s) { ids[s.id] = true; });
    var body = document.getElementById("artifacts");
    body.textContent = "";
    G.nodes.filter(function (n) { return n.kind === "artifact"; }).forEach(function (a) {
      var prod = related(a.id, "in", "produces").filter(function (x) { return ids[x]; });
      var cons = related(a.id, "out", "consumes").filter(function (x) { return ids[x]; });
      if (!prod.length && !cons.length) return;
      var tr = el("tr");
      tr.appendChild(el("th", {scope: "row"}, strip(a.id)));
      var td1 = el("td"), td2 = el("td");
      linkList(td1, prod); linkList(td2, cons);
      tr.appendChild(td1); tr.appendChild(td2);
      body.appendChild(tr);
    });
  }

  function drawRoles() {
    var ul = document.getElementById("roles");
    roles.forEach(function (r) {
      var n = related(r.id, "out", "recommends").length;
      var li = el("li");
      var b = el("button", {type: "button", "class": "link"}, r.name || strip(r.id));
      b.addEventListener("click", function () {
        document.getElementById("f-role").value = r.id;
        draw();
        document.getElementById("board").focus();
      });
      li.appendChild(b);
      li.appendChild(document.createTextNode(" (" + strip(r.id) + ", " + (r.family || "") + "): " + n + " recommended skills"));
      ul.appendChild(li);
    });
  }

  function draw() {
    var list = visible();
    var inst = list.filter(function (s) { return s.installed; }).length;
    document.getElementById("summary").textContent =
      list.length + " of " + skills.length + " skills shown, " + inst + " installed; " + phases.length + " phases, " + roles.length + " roles.";
    drawBoard(list);
    drawArtifacts(list);
  }

  function select(id) {
    selected = id;
    Array.prototype.forEach.call(document.querySelectorAll(".skill"), function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-id") === id));
    });
    drawDetail();
  }

  fill("f-role", roles.map(function (r) { return [r.id, r.name || strip(r.id)]; }));
  fill("f-phase", phases.map(function (p) { return [p, p]; }));
  var sources = {}; skills.forEach(function (s) { sources[s.source] = true; });
  fill("f-source", Object.keys(sources).sort().map(function (x) { return [x, x]; }));
  var form = document.getElementById("filters");
  form.addEventListener("input", draw);
  form.addEventListener("change", draw);
  form.addEventListener("reset", function () { setTimeout(draw, 0); });
  form.addEventListener("submit", function (e) { e.preventDefault(); });
  var q = document.getElementById("q");
  document.addEventListener("keydown", function (e) {
    var typing = /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName);
    if (e.key === "/" && !typing) { e.preventDefault(); q.focus(); }
    else if (e.key === "Escape" && document.activeElement === q) { q.value = ""; draw(); }
  });
  drawRoles();
  draw();
})();
</script>
</body>
</html>
"""


def graph_html(graph: dict) -> str:
    """Render graph_json output as a page; '<' is escaped so data can never close the script tag."""
    data = json.dumps(graph, ensure_ascii=False).replace("<", "\\u003c")
    return PAGE.replace("__DATA__", data)

"""One self-contained HTML page for the skill graph: inline CSS and JS, no network."""

import json

PAGE = """<!doctype html>
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
.link { background: none; border: 0; padding: 0; color: var(--accent); text-decoration: underline; font: inherit; cursor: pointer; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 24px; }
th, td { text-align: left; border-bottom: 1px solid var(--line); padding: 4px 8px; vertical-align: top; }
</style>
</head>
<body>
<header>
<h1>Skill graph</h1>
<p class="muted" id="summary"></p>
</header>
<main>
<noscript><p>This page needs JavaScript to draw the graph. The same data is available with <code>open-skill graph --format json</code>.</p></noscript>
<section aria-labelledby="phases-h">
<h2 id="phases-h">Skills by phase</h2>
<div class="board" id="board"></div>
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
      ul.appendChild(el("li", {}, (r.name || strip(r.id)) + " (" + strip(r.id) + ", " + (r.family || "") + "): " + n + " recommended skills"));
    });
  }

  function draw() {
    var list = skills;
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

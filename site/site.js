// Motion and small interactions for the Open Skill Standard site. The page is complete without this file;
// every effect below is skipped when the visitor prefers reduced motion.
(function () {
  "use strict";
  var doc = document.documentElement;
  var calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine = window.matchMedia("(pointer: fine)").matches;
  doc.classList.add("js");

  // Copy buttons work with or without motion.
  document.querySelectorAll(".copy").forEach(function (b) {
    b.addEventListener("click", function () {
      var text = document.getElementById(b.dataset.copy).innerText;
      var label = b.textContent;
      var done = function (ok) {
        b.textContent = ok ? b.dataset.ok || "Copied" : b.dataset.fail || "Select and copy";
        setTimeout(function () { b.textContent = label; }, 1800);
      };
      try { navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); }); }
      catch (e) { done(false); }
    });
  });

  // Header state, scroll progress and scroll-linked tilts share one rAF-throttled handler.
  var header = document.querySelector("header.top");
  var bar = document.querySelector(".progress");
  var tilts = calm ? [] : Array.prototype.slice.call(document.querySelectorAll(".tilt .shot"));
  var ticking = false;
  function onScroll() {
    var y = window.scrollY, max = doc.scrollHeight - window.innerHeight;
    if (header) header.classList.toggle("scrolled", y > 8);
    if (bar) bar.style.transform = "scaleX(" + (max > 0 ? Math.min(1, y / max) : 0) + ")";
    tilts.forEach(function (el) {
      var r = el.getBoundingClientRect(), vh = window.innerHeight;
      var p = Math.min(1, Math.max(0, (vh - r.top) / (vh * 0.75)));   // 0 when it enters, 1 once well in view
      el.style.setProperty("--tx", (16 * (1 - p)).toFixed(2) + "deg");
      el.style.setProperty("--ts", (0.94 + 0.06 * p).toFixed(3));
    });
    ticking = false;
  }
  window.addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();

  // Current section in the navigation, and the step list beside the diagrams.
  if ("IntersectionObserver" in window) {
    var links = {};
    document.querySelectorAll("nav.links a[href^='#']").forEach(function (a) { links[a.getAttribute("href").slice(1)] = a; });
    var navIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var a = links[e.target.id];
        if (a) a.setAttribute("aria-current", e.isIntersecting ? "true" : "false");
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    Object.keys(links).forEach(function (id) { var s = document.getElementById(id); if (s) navIO.observe(s); });

    var steps = document.querySelectorAll(".steps li");
    var stepIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var n = +e.target.dataset.step;
        steps.forEach(function (li, i) { li.classList.toggle("on", i === n); });
      });
    }, { rootMargin: "-40% 0px -45% 0px" });
    document.querySelectorAll("[data-step]").forEach(function (el) { if (el.tagName !== "LI") stepIO.observe(el); });
  }

  if (calm || !("IntersectionObserver" in window)) {
    document.querySelectorAll(".reveal, .wipe").forEach(function (el) { el.classList.add("in"); });
    return;
  }

  // Staggered reveals and wipes as sections enter.
  var fired = false;
  var revealIO = new IntersectionObserver(function (entries) {
    fired = true;
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add("in"); revealIO.unobserve(e.target); }
    });
  }, { rootMargin: "0px 0px -10% 0px", threshold: 0.08 });
  document.querySelectorAll(".reveal, .wipe").forEach(function (el) { revealIO.observe(el); });
  // Safety net: if the observer never reports (some embedded or prerendered views), show everything.
  function failSafe() {
    setTimeout(function () {
      if (!fired) document.querySelectorAll(".reveal, .wipe").forEach(function (el) { el.classList.add("in"); });
    }, 4000);
  }
  if (document.visibilityState === "visible") failSafe();
  else document.addEventListener("visibilitychange", function once() {
    if (document.visibilityState !== "visible") return;
    document.removeEventListener("visibilitychange", once);
    failSafe();
  });

  // Count the stats up once, from 0 to the number the build wrote into the page.
  var countIO = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      countIO.unobserve(e.target);
      var el = e.target, end = parseInt(el.textContent, 10), t0 = null;
      if (!(end > 0)) return;
      (function step(t) {
        if (t0 === null) t0 = t;
        var k = Math.min(1, (t - t0) / 1300), eased = 1 - Math.pow(1 - k, 4);
        el.textContent = Math.round(end * eased);
        if (k < 1) requestAnimationFrame(step);
      })(performance.now());
    });
  }, { threshold: 0.6 });
  document.querySelectorAll("[data-count]").forEach(function (el) { countIO.observe(el); });

  if (!fine) return;

  // Spotlight that follows the cursor inside bento tiles.
  document.querySelectorAll(".tile").forEach(function (t) {
    t.addEventListener("pointermove", function (ev) {
      var r = t.getBoundingClientRect();
      t.style.setProperty("--mx", (ev.clientX - r.left) + "px");
      t.style.setProperty("--my", (ev.clientY - r.top) + "px");
    });
  });

  // The hero terminal leans slightly toward the cursor.
  var stage = document.querySelector(".hero .stage"), shot = stage && stage.querySelector(".shot");
  if (stage && shot) {
    stage.addEventListener("pointermove", function (ev) {
      var r = stage.getBoundingClientRect();
      var x = (ev.clientX - r.left) / r.width - 0.5, y = (ev.clientY - r.top) / r.height - 0.5;
      shot.style.transform = "rotateY(" + (x * 10 - 4).toFixed(2) + "deg) rotateX(" + (-y * 8 + 2).toFixed(2) + "deg)";
    });
    stage.addEventListener("pointerleave", function () { shot.style.transform = ""; });
  }
})();

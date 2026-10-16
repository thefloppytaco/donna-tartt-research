/* Client-side filtering for the catalogue index pages. Progressive enhancement:
   without JS every item is still listed and linked. */
(function () {
  "use strict";

  document.querySelectorAll("[data-filter-scope]").forEach(function (scope) {
    var input  = scope.querySelector("[data-filter-input]");
    var chips  = Array.prototype.slice.call(scope.querySelectorAll("[data-chip]"));
    var items  = Array.prototype.slice.call(scope.querySelectorAll("[data-search]"));
    var count  = scope.querySelector("[data-filter-count]");
    var blocks = Array.prototype.slice.call(scope.querySelectorAll("[data-block]"));
    var empty  = scope.querySelector("[data-filter-empty]");
    var active = null;

    function norm(s) {
      return (s || "").toLowerCase()
        .normalize("NFD").replace(/[̀-ͯ]/g, "");
    }

    function apply() {
      var q = norm(input ? input.value.trim() : "");
      var terms = q ? q.split(/\s+/) : [];
      var shown = 0;
      items.forEach(function (el) {
        var hay = el.getAttribute("data-search");
        var ok = (!active || el.getAttribute("data-group") === active) &&
                 terms.every(function (t) { return hay.indexOf(t) !== -1; });
        el.hidden = !ok;
        if (ok) { shown++; }
      });
      blocks.forEach(function (b) {
        var any = b.querySelector("[data-search]:not([hidden])");
        b.hidden = !any;
      });
      if (count) {
        count.textContent = shown === items.length
          ? items.length + " items"
          : shown + " of " + items.length;
      }
      if (empty) { empty.hidden = shown !== 0; }
    }

    if (input) {
      input.addEventListener("input", apply);
      input.addEventListener("search", apply);
    }
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        var g = chip.getAttribute("data-group");
        active = active === g ? null : g;
        chips.forEach(function (c) {
          c.setAttribute("aria-pressed", c.getAttribute("data-group") === active ? "true" : "false");
        });
        apply();
      });
    });
    apply();
  });

  /* Image fallback. Every <img> generated from the repository carries the path
     of the original it was derived from. If the derivative is missing — the
     docs/assets/img/ tree has not been built, or a file was pruned — swap in
     the original from the repository so the page still shows the artifact. */
  function fallBack(el) {
    var origin = el.getAttribute("data-origin");
    if (!origin || el.dataset.fellBack) { return; }
    el.dataset.fellBack = "1";
    el.removeAttribute("srcset");
    el.src = "https://raw.githubusercontent.com/thefloppytaco/donna-tartt-research/main/" + origin;
  }

  /* "error" does not bubble, hence the capture-phase listener... */
  document.addEventListener("error", function (ev) {
    if (ev.target && ev.target.tagName === "IMG") { fallBack(ev.target); }
  }, true);

  /* ...and this script is deferred, so sweep whatever already failed. */
  function sweep() {
    document.querySelectorAll("img[data-origin]").forEach(function (img) {
      if (img.complete && img.naturalWidth === 0) { fallBack(img); }
    });
  }

  sweep();
  window.addEventListener("load", sweep);

  /* "Copy citation" on item pages */
  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var src = document.getElementById(btn.getAttribute("data-copy"));
      if (!src || !navigator.clipboard) { return; }
      navigator.clipboard.writeText(src.textContent.trim()).then(function () {
        var was = btn.textContent;
        btn.textContent = "Copied";
        setTimeout(function () { btn.textContent = was; }, 1600);
      });
    });
  });
})();

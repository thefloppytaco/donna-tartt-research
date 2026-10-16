"""Stylesheet and client script for the static site (no build step, no CDN)."""

CSS = r"""/* ===========================================================================
   Donna Tartt — A Collector's Reference
   Dark-academia theme. No webfonts, no frameworks: system serifs only, so the
   site renders identically offline and costs nothing to load.
   =========================================================================== */

:root {
  --ink:        #14110e;
  --ink-2:      #1b1713;
  --ink-3:      #231e19;
  --ink-4:      #2b241e;
  --rule:       #3a3129;
  --rule-soft:  #2a241f;
  --parchment:      #e9e1d3;
  --parchment-mid:  #cfc5b4;
  --parchment-dim:  #a99e8c;
  --gold:       #d9bd6a;
  --gold-deep:  #b8952f;
  --oxblood:    #9c2b2b;
  --oxblood-lo: #6d1f1f;
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua",
           "URW Palladio L", P052, Georgia, "Times New Roman", serif;
  --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
          "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
  --measure: 72ch;
  --page: 1180px;
}

*, *::before, *::after { box-sizing: border-box; }

html { -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }

body {
  margin: 0;
  background: var(--ink);
  background-image:
    radial-gradient(1200px 620px at 50% -12%, #2a221b 0%, transparent 70%),
    linear-gradient(180deg, #171310 0%, var(--ink) 38%);
  background-repeat: no-repeat;
  color: var(--parchment);
  font-family: var(--serif);
  font-size: 1.0625rem;
  line-height: 1.68;
  text-rendering: optimizeLegibility;
}

/* --------------------------------------------------------------- typography */
h1, h2, h3, h4, h5, h6 { font-family: var(--serif); font-weight: 600; line-height: 1.22;
  color: #f2ebdd; margin: 2.2em 0 .6em; letter-spacing: .005em; scroll-margin-top: 5.5rem; }
h1 { font-size: clamp(1.85rem, 1.2rem + 2.2vw, 2.85rem); margin-top: 0; letter-spacing: -.01em; }
h2 { font-size: clamp(1.35rem, 1.1rem + 1vw, 1.72rem); }
h3 { font-size: 1.22rem; }
h4, h5, h6 { font-size: 1.06rem; color: var(--parchment); }
h2 + h3, h3 + h4 { margin-top: 1.4em; }

p { margin: 0 0 1.05em; }
strong { color: #f6f0e3; font-weight: 600; }
em { font-style: italic; }
small, .small { font-size: .875rem; color: var(--parchment-dim); }

a { color: var(--gold); text-decoration-line: underline;
  text-decoration-color: rgba(217,189,106,.38); text-decoration-thickness: 1px;
  text-underline-offset: .18em; }
a:hover { color: #f0dba0; text-decoration-color: rgba(240,219,160,.85); }
a:focus-visible, button:focus-visible, input:focus-visible, summary:focus-visible {
  outline: 2px solid var(--gold); outline-offset: 2px; border-radius: 2px; }

code, kbd { font-family: var(--mono); font-size: .86em; background: #221c17;
  border: 1px solid var(--rule-soft); border-radius: 3px; padding: .08em .34em;
  color: #e3d6bb; word-break: break-word; }

blockquote { margin: 1.5em 0; padding: .1em 0 .1em 1.2em;
  border-left: 2px solid var(--oxblood); color: var(--parchment-mid); font-style: italic; }
blockquote p:last-child { margin-bottom: 0; }

hr.rule { border: 0; height: 1px; margin: 2.4em auto;
  background: linear-gradient(90deg, transparent, var(--rule) 18%, var(--rule) 82%, transparent); }

ul, ol { margin: 0 0 1.1em; padding-left: 1.5em; }
li { margin: .3em 0; }
li > ul, li > ol { margin: .3em 0 .4em; }

.anchor { margin-left: .4em; font-size: .62em; color: var(--rule);
  text-decoration: none; opacity: 0; transition: opacity .15s; vertical-align: .18em; }
h1:hover .anchor, h2:hover .anchor, h3:hover .anchor,
h4:hover .anchor, h5:hover .anchor, h6:hover .anchor { opacity: 1; }

/* ------------------------------------------------------------------- layout */
.wrap { max-width: var(--page); margin: 0 auto; padding: 0 clamp(1rem, 4vw, 2.5rem); }
.prose { max-width: var(--measure); }
.prose-wide { max-width: 90ch; }

/* ------------------------------------------------------------------- header */
.masthead { position: sticky; top: 0; z-index: 50;
  background: rgba(16,13,11,.93); backdrop-filter: saturate(140%) blur(8px);
  border-bottom: 1px solid var(--rule-soft);
  box-shadow: 0 1px 0 rgba(217,189,106,.1); }
.masthead-in { max-width: var(--page); margin: 0 auto; padding: .55rem clamp(1rem, 4vw, 2.5rem);
  display: flex; align-items: baseline; gap: 1.4rem; flex-wrap: wrap; }
.brand { font-size: 1.02rem; font-weight: 600; color: #f2ebdd; text-decoration: none;
  letter-spacing: .09em; text-transform: uppercase; white-space: nowrap; }
.brand:hover { color: var(--gold); }
.brand .brand-sub { display: block; font-size: .62rem; letter-spacing: .22em;
  color: var(--parchment-dim); font-weight: 400; margin-top: .15em; }
nav.topnav { margin-left: auto; overflow-x: auto; scrollbar-width: none; }
nav.topnav::-webkit-scrollbar { display: none; }
nav.topnav ul { display: flex; gap: 1.15rem; list-style: none; margin: 0; padding: 0; }
nav.topnav a { font-size: .775rem; letter-spacing: .14em; text-transform: uppercase;
  color: var(--parchment-mid); text-decoration: none; white-space: nowrap;
  padding: .3rem 0; border-bottom: 1px solid transparent; }
nav.topnav a:hover { color: var(--gold); }
nav.topnav a[aria-current="page"] { color: var(--gold); border-bottom-color: var(--gold-deep); }

/* --------------------------------------------------------------------- hero */
.hero { padding: clamp(2.6rem, 7vw, 5.4rem) 0 clamp(1.8rem, 4vw, 3rem); text-align: center;
  border-bottom: 1px solid var(--rule-soft); }
.hero .eyebrow { font-size: .72rem; letter-spacing: .36em; text-transform: uppercase;
  color: var(--gold-deep); margin: 0 0 1.1rem; }
.hero h1 { font-size: clamp(2.1rem, 1.1rem + 4.2vw, 4rem); letter-spacing: -.015em;
  margin: 0 0 .5rem; }
.hero .dek { max-width: 62ch; margin: 0 auto; color: var(--parchment-mid);
  font-size: clamp(1.02rem, .98rem + .3vw, 1.2rem); }
.hero .dek a { color: var(--gold); }
.flourish { display: block; margin: 1.6rem auto; width: 112px; height: 10px; opacity: .8; }

/* ------------------------------------------------------------------ eyebrow */
.page-head { padding: clamp(2rem, 5vw, 3.4rem) 0 1.2rem; border-bottom: 1px solid var(--rule-soft);
  margin-bottom: 2.2rem; }
.page-head .eyebrow, .eyebrow { font-size: .7rem; letter-spacing: .3em; text-transform: uppercase;
  color: var(--gold-deep); margin: 0 0 .7rem; }
.page-head h1 { margin: 0 0 .5rem; }
.page-head .dek { max-width: 76ch; color: var(--parchment-mid); margin: 0; }

.crumbs { font-size: .8rem; color: var(--parchment-dim); margin: 0 0 1.4rem; letter-spacing: .02em; }
.crumbs a { color: var(--parchment-mid); }
.crumbs span { opacity: .5; margin: 0 .45em; }

/* -------------------------------------------------------------------- stats */
.stats { display: grid; gap: 1px; background: var(--rule-soft);
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  border: 1px solid var(--rule-soft); margin: 2.6rem 0; }
.stats div { background: var(--ink-2); padding: 1.15rem .9rem; text-align: center; }
.stats b { display: block; font-size: 1.85rem; color: var(--gold); font-weight: 600;
  letter-spacing: -.01em; line-height: 1.1; }
.stats span { font-size: .715rem; letter-spacing: .17em; text-transform: uppercase;
  color: var(--parchment-dim); }

/* ---------------------------------------------------------------- shelf/hero covers */
.shelf { display: flex; gap: clamp(.6rem, 2vw, 1.6rem); justify-content: center;
  align-items: flex-end; flex-wrap: wrap; margin: 2.4rem 0 .5rem; }
.shelf a { display: block; text-decoration: none; }
.shelf img { display: block; height: clamp(130px, 20vw, 232px); width: auto;
  border: 1px solid var(--rule); box-shadow: 0 10px 26px rgba(0,0,0,.55);
  transition: transform .2s ease, box-shadow .2s ease; }
.shelf a:hover img { transform: translateY(-5px);
  box-shadow: 0 16px 34px rgba(0,0,0,.65); border-color: var(--gold-deep); }

/* ---------------------------------------------------------------- nav cards */
.cards { display: grid; gap: 1.1rem; margin: 2rem 0;
  grid-template-columns: repeat(auto-fit, minmax(255px, 1fr)); }
.card { display: block; background: var(--ink-2); border: 1px solid var(--rule-soft);
  padding: 1.25rem 1.3rem 1.35rem; text-decoration: none; color: inherit;
  transition: border-color .18s, background .18s, transform .18s; }
a.card:hover { border-color: var(--gold-deep); background: var(--ink-3); transform: translateY(-2px); }
.card h3 { margin: 0 0 .4rem; font-size: 1.1rem; color: #f2ebdd; }
a.card:hover h3 { color: var(--gold); }
.card p { margin: 0; font-size: .92rem; color: var(--parchment-dim); line-height: 1.55; }
.card .count { font-size: .7rem; letter-spacing: .18em; text-transform: uppercase;
  color: var(--gold-deep); display: block; margin-bottom: .55rem; }

/* ------------------------------------------------------------------ gallery */
.gallery { display: grid; gap: clamp(.9rem, 2vw, 1.5rem); margin: 1.6rem 0 2.6rem;
  grid-template-columns: repeat(auto-fill, minmax(146px, 1fr)); }
.gallery.wide { grid-template-columns: repeat(auto-fill, minmax(178px, 1fr)); }
.tile { display: flex; flex-direction: column; text-decoration: none; color: inherit; }
.tile .frame { background: #100d0b; border: 1px solid var(--rule-soft);
  aspect-ratio: 3 / 4; display: flex; align-items: center; justify-content: center;
  overflow: hidden; transition: border-color .18s, box-shadow .18s; }
.tile img { max-width: 100%; max-height: 100%; width: auto; height: auto; display: block;
  transition: transform .25s ease; }
.tile:hover .frame { border-color: var(--gold-deep); box-shadow: 0 8px 22px rgba(0,0,0,.5); }
.tile:hover img { transform: scale(1.035); }
.tile .nocover { font-size: .72rem; letter-spacing: .14em; text-transform: uppercase;
  color: #5d5347; text-align: center; padding: .8rem; }
.tile .label { padding: .55rem .1rem 0; font-size: .855rem; line-height: 1.35; color: var(--parchment); }
.tile:hover .label { color: var(--gold); }
.tile .sub { font-size: .735rem; color: var(--parchment-dim); margin-top: .18rem; line-height: 1.4; }
.tile .flag { font-size: .66rem; letter-spacing: .12em; text-transform: uppercase;
  color: var(--oxblood); margin-top: .2rem; }

/* ----------------------------------------------------------------- listings */
.listing { list-style: none; margin: 1.4rem 0 2.6rem; padding: 0;
  border-top: 1px solid var(--rule-soft); }
.listing > li { border-bottom: 1px solid var(--rule-soft); }
.listing a.row { display: grid; grid-template-columns: 58px 1fr auto; gap: 1rem;
  align-items: center; padding: .85rem .4rem; text-decoration: none; color: inherit; }
.listing a.row:hover { background: var(--ink-2); }
.listing .mini { width: 58px; height: 74px; background: #100d0b; border: 1px solid var(--rule-soft);
  display: flex; align-items: center; justify-content: center; overflow: hidden; }
.listing .mini img { max-width: 100%; max-height: 100%; }
.listing .mini.empty::after { content: "—"; color: #4e463c; }
.listing .t { font-size: .98rem; line-height: 1.4; }
.listing a.row:hover .t { color: var(--gold); }
.listing .s { font-size: .78rem; color: var(--parchment-dim); margin-top: .18rem; }
.listing .y { font-family: var(--mono); font-size: .8rem; color: var(--parchment-dim);
  white-space: nowrap; }
@media (max-width: 560px) {
  .listing a.row { grid-template-columns: 44px 1fr; }
  .listing .mini { width: 44px; height: 58px; }
  .listing .y { display: none; }
}

/* --------------------------------------------------------------- filter bar */
.filterbar { display: flex; gap: .7rem; flex-wrap: wrap; align-items: center;
  margin: 0 0 1.4rem; padding: .85rem 0 1rem; border-bottom: 1px solid var(--rule-soft); }
.filterbar input[type="search"] { flex: 1 1 240px; min-width: 0; background: var(--ink-2);
  border: 1px solid var(--rule); color: var(--parchment); font-family: var(--serif);
  font-size: .95rem; padding: .5rem .75rem; border-radius: 2px; }
.filterbar input::placeholder { color: #6f6557; }
.chips { display: flex; gap: .4rem; flex-wrap: wrap; }
.chip { background: transparent; border: 1px solid var(--rule); color: var(--parchment-mid);
  font-family: var(--sans); font-size: .7rem; letter-spacing: .12em; text-transform: uppercase;
  padding: .42rem .72rem; cursor: pointer; border-radius: 2px; }
.chip:hover { border-color: var(--gold-deep); color: var(--gold); }
.chip[aria-pressed="true"] { background: var(--oxblood-lo); border-color: var(--oxblood);
  color: #f6ecdc; }
.filter-count { font-size: .78rem; color: var(--parchment-dim); margin-left: auto;
  font-variant-numeric: tabular-nums; }
.empty-note { color: var(--parchment-dim); font-style: italic; padding: 1.6rem 0; }

/* ------------------------------------------------------------- group header */
.group-head { display: flex; align-items: baseline; gap: .9rem; flex-wrap: wrap;
  margin: 2.8rem 0 .2rem; padding-bottom: .5rem; border-bottom: 1px solid var(--rule-soft); }
.group-head h2 { margin: 0; }
.group-head .n { font-size: .72rem; letter-spacing: .16em; text-transform: uppercase;
  color: var(--parchment-dim); }
.group-head .more { margin-left: auto; font-size: .8rem; }

/* ---------------------------------------------------------------- item page */
.item-head { display: grid; grid-template-columns: minmax(0, 300px) minmax(0, 1fr);
  gap: clamp(1.4rem, 4vw, 3rem); align-items: start; margin-bottom: 2.6rem; }
@media (max-width: 760px) { .item-head { grid-template-columns: 1fr; } }
.item-head .cover { background: #100d0b; border: 1px solid var(--rule);
  padding: .55rem; box-shadow: 0 14px 34px rgba(0,0,0,.5); }
.item-head .cover img { display: block; width: 100%; height: auto; }
.item-head .cover figcaption { font-size: .72rem; color: var(--parchment-dim);
  padding: .5rem .2rem 0; text-align: center; }
.item-head .nocover-box { border: 1px dashed var(--rule); padding: 2.2rem 1rem; text-align: center;
  color: var(--parchment-dim); font-size: .85rem; }
.item-title { margin: 0 0 .7rem; font-size: clamp(1.5rem, 1.1rem + 1.4vw, 2.1rem); }
.item-kicker { font-size: .72rem; letter-spacing: .2em; text-transform: uppercase;
  color: var(--gold-deep); margin: 0 0 .8rem; }
.item-kicker code { background: none; border: 0; color: var(--gold); padding: 0; letter-spacing: .1em; }

.meta { width: 100%; border-collapse: collapse; margin: 1.2rem 0 1.6rem; font-size: .92rem; }
.meta th, .meta td { text-align: left; padding: .46rem .7rem .46rem 0;
  border-bottom: 1px solid var(--rule-soft); vertical-align: top; }
.meta th { width: 8.6rem; font-weight: 400; color: var(--parchment-dim); font-size: .78rem;
  letter-spacing: .1em; text-transform: uppercase; white-space: nowrap; }
.meta td { color: var(--parchment); }

.actions { display: flex; flex-wrap: wrap; gap: .55rem; margin: 1.2rem 0 0; }
.btn { display: inline-block; font-family: var(--sans); font-size: .74rem; letter-spacing: .13em;
  text-transform: uppercase; padding: .55rem .9rem; border: 1px solid var(--rule);
  color: var(--parchment-mid); text-decoration: none; background: var(--ink-2); border-radius: 2px; }
.btn:hover { border-color: var(--gold-deep); color: var(--gold); background: var(--ink-3); }
.btn.primary { border-color: var(--oxblood); background: var(--oxblood-lo); color: #f7eedf; }
.btn.primary:hover { background: #7e2525; color: #fff; }

/* ------------------------------------------------------------------ section */
.section { margin: 3rem 0; }
.section > h2 { display: flex; align-items: baseline; gap: .8rem; margin-top: 0; }
.section-label { font-size: .7rem; letter-spacing: .28em; text-transform: uppercase;
  color: var(--gold-deep); border-top: 1px solid var(--rule-soft); padding-top: .9rem;
  margin: 2.8rem 0 1rem; display: block; }

/* -------------------------------------------------------------- source list */
.sources { list-style: none; padding: 0; margin: .8rem 0 1.2rem; }
.sources li { padding: .42rem 0 .42rem 1.5rem; position: relative; font-size: .93rem;
  border-bottom: 1px solid var(--rule-soft); }
.sources li::before { content: "❧"; position: absolute; left: 0; top: .42rem;
  color: var(--gold-deep); font-size: .82rem; }
.sources .kind { font-size: .7rem; letter-spacing: .1em; text-transform: uppercase;
  color: var(--parchment-dim); margin-left: .4rem; white-space: nowrap; }

/* -------------------------------------------------------------- long-form text */
.fulltext { max-width: var(--measure); font-size: 1.085rem; line-height: 1.78; }
.fulltext p { margin: 0 0 1.25em; }
.fulltext > p:first-of-type::first-letter { float: left; font-size: 3.5em; line-height: .84;
  padding: .06em .09em 0 0; color: var(--gold); font-weight: 600; }
.fulltext h2, .fulltext h3, .fulltext h4 { margin-top: 2em; }
.fulltext strong { color: #f7f1e4; }
.fulltext em { color: var(--parchment); }
.transcript { max-width: var(--measure); font-size: 1.055rem; line-height: 1.76; }
.transcript p > strong:only-child, .transcript p > strong:first-child {
  color: var(--gold); }
.verse { white-space: pre-wrap; font-size: 1.02rem; line-height: 1.72; margin: 1.4rem 0;
  padding-left: 1.1rem; border-left: 1px solid var(--rule); color: var(--parchment); }

/* --------------------------------------------------------------- provenance */
.provenance { background: var(--ink-2); border: 1px solid var(--rule-soft);
  border-left: 2px solid var(--gold-deep); padding: 1rem 1.15rem; margin: 2rem 0;
  font-size: .875rem; color: var(--parchment-mid); }
.provenance b { color: var(--parchment); font-weight: 600; }
.provenance p { margin: 0 0 .5em; }
.provenance p:last-child { margin: 0; }
.provenance code { font-size: .8em; }

.callout { border: 1px solid var(--rule); border-left: 3px solid var(--oxblood);
  background: rgba(156,43,43,.08); padding: 1rem 1.15rem; margin: 1.6rem 0; font-size: .93rem; }
.callout.note { border-left-color: var(--gold-deep); background: rgba(217,189,106,.06); }
.callout b { color: #f6efe1; }
.callout p:last-child { margin-bottom: 0; }

/* ------------------------------------------------------------------- tables */
.table-wrap { overflow-x: auto; margin: 1.5rem 0; border: 1px solid var(--rule-soft); }
.table-wrap table { border-collapse: collapse; width: 100%; font-size: .9rem; min-width: 32rem; }
.table-wrap th, .table-wrap td { padding: .55rem .8rem; text-align: left; vertical-align: top;
  border-bottom: 1px solid var(--rule-soft); }
.table-wrap thead th { background: var(--ink-3); color: var(--gold); font-weight: 600;
  font-size: .76rem; letter-spacing: .1em; text-transform: uppercase; white-space: nowrap; }
.table-wrap tbody tr:nth-child(even) { background: rgba(255,255,255,.015); }
.table-wrap tbody tr:hover { background: rgba(217,189,106,.045); }
.table-wrap td code { font-size: .8em; }

/* -------------------------------------------------------------------- plates */
figure.plate { margin: 2rem 0; }
figure.plate img { display: block; max-width: 100%; height: auto; margin: 0 auto;
  border: 1px solid var(--rule); background: #100d0b; }
figure.plate figcaption { font-size: .8rem; color: var(--parchment-dim); margin-top: .7rem;
  line-height: 1.5; max-width: 68ch; }
a.plate-link { display: block; text-decoration: none; }

/* --------------------------------------------------------------- reference */
.ref-layout { display: grid; grid-template-columns: 250px minmax(0, 1fr);
  gap: clamp(1.5rem, 4vw, 3.2rem); align-items: start; }
@media (max-width: 900px) { .ref-layout { grid-template-columns: 1fr; } }
.ref-side { position: sticky; top: 5rem; font-size: .86rem; max-height: calc(100vh - 7rem);
  overflow-y: auto; padding-right: .4rem; }
@media (max-width: 900px) { .ref-side { position: static; max-height: none; border-bottom:
  1px solid var(--rule-soft); padding-bottom: 1rem; } }
.ref-side h2 { font-size: .7rem; letter-spacing: .22em; text-transform: uppercase;
  color: var(--gold-deep); margin: 0 0 .7rem; }
.ref-side ol, .ref-side ul { list-style: none; margin: 0; padding: 0; }
.ref-side li { margin: 0; }
.ref-side a { display: block; padding: .3rem .5rem .3rem .65rem; color: var(--parchment-mid);
  text-decoration: none; border-left: 1px solid var(--rule-soft); line-height: 1.4; }
.ref-side a:hover { color: var(--gold); border-left-color: var(--gold-deep);
  background: var(--ink-2); }
.ref-side a[aria-current="page"] { color: var(--gold); border-left-color: var(--gold);
  background: var(--ink-2); }
.ref-side .sub a { padding-left: 1.3rem; font-size: .93em; color: var(--parchment-dim); }
.ref-body { min-width: 0; }
.ref-body h2 { border-top: 1px solid var(--rule-soft); padding-top: 1.4rem; }
.ref-body h2:first-child { border-top: 0; padding-top: 0; }
.fnref { font-size: .78em; vertical-align: .32em; color: var(--gold-deep);
  text-decoration: none; padding: 0 .08em; }
.fnref:hover { color: var(--gold); }
.fnum { color: var(--gold-deep); font-variant-numeric: tabular-nums; margin-right: .2em; }
#footnote-list li { padding: .5rem 0; border-bottom: 1px solid var(--rule-soft);
  font-size: .9rem; color: var(--parchment-mid); }
.pager { display: flex; justify-content: space-between; gap: 1rem; margin: 3.2rem 0 0;
  padding-top: 1.4rem; border-top: 1px solid var(--rule-soft); font-size: .9rem; }
.pager a { max-width: 46%; }
.pager .next { margin-left: auto; text-align: right; }
.pager .lbl { display: block; font-size: .66rem; letter-spacing: .2em; text-transform: uppercase;
  color: var(--parchment-dim); margin-bottom: .2rem; }

/* ------------------------------------------------------------------- footer */
footer.site { margin-top: 4.5rem; border-top: 1px solid var(--rule-soft);
  background: #110e0c; padding: 2.6rem 0 3rem; font-size: .875rem;
  color: var(--parchment-dim); }
footer.site .cols { display: grid; gap: 2rem;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
footer.site h3 { font-size: .68rem; letter-spacing: .22em; text-transform: uppercase;
  color: var(--gold-deep); margin: 0 0 .7rem; }
footer.site ul { list-style: none; margin: 0; padding: 0; }
footer.site li { margin: .3rem 0; }
footer.site a { color: var(--parchment-mid); }
footer.site a:hover { color: var(--gold); }
footer.site .colophon { margin-top: 2.4rem; padding-top: 1.4rem;
  border-top: 1px solid var(--rule-soft); line-height: 1.7; max-width: 80ch; }

.skip { position: absolute; left: -9999px; top: 0; background: var(--ink-3);
  color: var(--gold); padding: .7rem 1rem; z-index: 100; }
.skip:focus { left: .5rem; top: .5rem; }

@media print {
  body { background: #fff; color: #000; }
  .masthead, nav.topnav, footer.site, .filterbar, .pager, .actions { display: none; }
  a { color: #000; }
}
"""

JS = r"""/* Client-side filtering for the catalogue index pages. Progressive enhancement:
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
    el.src = "__RAW_BASE__" + origin;
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
"""

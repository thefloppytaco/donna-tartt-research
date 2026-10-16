#!/usr/bin/env python3
"""
Builds the GitHub Pages website in `docs/` from the research database.

    python3 scripts/build_site.py [--clean] [-v]

Everything on the site is generated from files already in the repository —
`data/cover_manifest.csv`, the master reference, the Tier B list, the interview
transcripts, the contribution excerpts and the primary-source captures under
`assets/`. The generator invents no facts: where a page states something it
either comes from one of those files or links to it.

Primary sources are cited two ways. Images are republished as downscaled
derivatives under `docs/assets/img/` (the full-resolution original stays in the
repository and every plate links to it). Everything else — the dealer/press
captures, auction PDFs, excerpt PDFs, transcripts — is cited by a link to the
file in the repository, so a reader can always reach the artifact itself.
"""
import argparse
import html as esc
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sitelib import corpus as C                       # noqa: E402
from sitelib import markdown as md                    # noqa: E402
from sitelib import theme                             # noqa: E402
from sitelib.images import ImageSet                   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs")

REPO = "https://github.com/thefloppytaco/donna-tartt-research"
BLOB = REPO + "/blob/main/"
RAW = "https://raw.githubusercontent.com/thefloppytaco/donna-tartt-research/main/"
TREE = REPO + "/tree/main/"
SITE_URL = "https://thefloppytaco.github.io/donna-tartt-research/"

TAGLINE = ("A sourced reference to every published edition, signed copy, essay, "
           "contribution and on-record interview of the American novelist "
           "Donna Tartt — each tied to the primary source that backs it.")

NAV = [
    ("editions", "editions/index.html", "Editions"),
    ("signed", "signed/index.html", "Signed copies"),
    ("essays", "essays/index.html", "Essays"),
    ("contributions", "contributions/index.html", "Contributions"),
    ("interviews", "interviews/index.html", "Interviews"),
    ("press", "press/index.html", "Press"),
    ("about", "about/index.html", "About Tartt"),
    ("reference", "reference/index.html", "Reference"),
]

SECTION_TITLE = {
    "editions": "Editions",
    "essays": "Essays & short fiction",
    "contributions": "Introductions & contributions",
    "press": "Press & ephemera",
}

FAVICON = (
    "data:image/svg+xml,"
    "%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2032%2032'%3E"
    "%3Crect%20width='32'%20height='32'%20fill='%2314110e'/%3E"
    "%3Ctext%20x='16'%20y='23'%20font-family='Georgia,serif'%20font-size='21'"
    "%20font-weight='600'%20fill='%23d9bd6a'%20text-anchor='middle'%3ET%3C/text%3E%3C/svg%3E"
)

FLOURISH = ('<svg class="flourish" viewBox="0 0 112 10" aria-hidden="true">'
            '<path d="M0 5h44M68 5h44" stroke="#3a3129" stroke-width="1"/>'
            '<path d="M56 1l3.4 4L56 9l-3.4-4z" fill="#b8952f"/>'
            '<circle cx="47" cy="5" r="1.4" fill="#3a3129"/>'
            '<circle cx="65" cy="5" r="1.4" fill="#3a3129"/></svg>')


# ============================================================ small helpers
def e(text):
    return esc.escape(str(text or ""), quote=True)


def write(path, text):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(text)


def norm_search(*bits):
    blob = " ".join(str(b) for b in bits if b)
    return re.sub(r"\s+", " ", md.plain(blob)).strip().lower()


def _cap_key(text):
    return re.sub(r"\s+", " ", md.plain(text).strip().strip("*_ ")).lower()


def dedupe_captions(text):
    """Drop the caption lines the reference repeats under its figures.

    The master reference was converted from a word processor, which left most
    plates with their caption three times over: once as the image's alt text and
    title, then again as a bare paragraph, then again in italics. GitHub renders
    all three. Here the figure keeps its caption and the echoes are dropped.
    """
    out, alt, gap = [], None, 0
    for line in text.split("\n"):
        m = re.search(r"!\[([^\]]{12,})\]\(", line)
        if m:
            alt, gap = _cap_key(m.group(1)), 0
            out.append(line)
            continue
        if alt and line.strip():
            gap += 1
            if gap <= 4 and _cap_key(line) == alt:
                continue
            if gap > 4:
                alt = None
        out.append(line)
    return "\n".join(out)


def _clip(text, limit):
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def plural(n, word, suffix="s"):
    return f"{n} {word}{'' if n == 1 else suffix}"


def short_date(value):
    """The date out of a provenance line that may carry a parenthetical gloss."""
    m = re.search(r"~?\d{4}(?:-\d{2}){0,2}", value or "")
    return m.group(0) if m else md.plain(value or "")[:24]


YEAR_RE = re.compile(r"^(?:~|c\.)?\d{4}")


def year_label(value):
    """The year as it should be shown: a real year, a short gloss, or nothing."""
    value = (value or "").strip()
    m = YEAR_RE.match(value)
    if m:
        return m.group(0)
    return value if 0 < len(value) <= 12 else ""


def isbn_ok(value):
    return bool(re.fullmatch(r"[0-9Xx\- ]{9,20}", (value or "").strip()))


def row_suspect(it):
    """True when a manifest row's columns look shifted (an unescaped comma)."""
    return (len(it.country) > 14 or len(it.language) > 14
            or (it.isbn13 and not isbn_ok(it.isbn13))
            or (it.isbn10 and not isbn_ok(it.isbn10)))


def blob_url(repo_rel):
    return BLOB + repo_rel.lstrip("/")


def origin_attr(rel):
    """The repository original an image was derived from.

    `theme.JS` falls back to it when the derivative under `docs/assets/img/` is
    missing, so a page still shows its plates if the image tree was never built.
    """
    return f'data-origin="{e("assets/images/" + rel)}"'


class P:
    """A page being written: knows its own path, so it can make relative links."""

    def __init__(self, site, path):
        self.site = site
        self.path = path
        self.depth = path.count("/")

    def u(self, target):
        if target.startswith(("http://", "https://", "#", "mailto:", "data:")):
            return target
        return "../" * self.depth + target

    def img(self, rel, thumb=False):
        return self.u(self.site.img.url(rel, thumb=thumb))


# ============================================================ reference paging
CHAPTER_MAX_CHARS = 70_000      # source characters before a chapter is split


def paginate(sections, max_chars=CHAPTER_MAX_CHARS):
    """Split any reference chapter too long to read as one page into parts.

    Only the unusually large chapters are affected (§7, which runs to ~1,200
    source lines). Parts break on subsection boundaries and are packed to a
    near-even size; part one keeps the chapter's slug, so links to the chapter
    still land on its opening page.
    """
    out = []
    for sec in sections:
        if len(sec.body_md) <= max_chars:
            out.append(sec)
            continue
        blocks, cur = [], []
        for line in sec.lines:
            if re.match(r"^###\s+\S", line) and cur:
                blocks.append(cur)
                cur = []
            cur.append(line)
        if cur:
            blocks.append(cur)
        parts_wanted = max(2, -(-len(sec.body_md) // max_chars))
        target = len(sec.body_md) / parts_wanted
        parts, cur, size = [], [], 0
        for block in blocks:
            block_len = sum(len(l) + 1 for l in block)
            if cur and size + block_len > target and len(parts) < parts_wanted - 1:
                parts.append(cur)
                cur, size = [], 0
            cur += block
            size += block_len
        if cur:
            parts.append(cur)
        total = len(parts)
        for i, lines in enumerate(parts, 1):
            title = sec.title if i == 1 else f"{sec.title} (part {i} of {total})"
            slug = sec.slug if i == 1 else f"{sec.slug}-part-{i}"
            part = C.RefSection(sec.token, title, lines, slug)
            part.part, part.part_count = i, total
            out.append(part)
    return out


# ================================================================== rewriting
class SiteRewriter(md.Rewriter):
    """Turns repo-relative Markdown links into working site / repository links."""

    def __init__(self, page, *, same_page_anchors=False, footnote_page=None):
        self.p = page
        self.site = page.site
        self.same_page_anchors = same_page_anchors
        self.footnote_page = footnote_page

    # ------------------------------------------------------------------ links
    def link(self, href):
        href = (href or "").strip()
        if not href:
            return None
        if href.startswith(("http://", "https://", "mailto:")):
            return href
        if href.startswith("#"):
            return self._anchor(href[1:])
        path, _, frag = href.partition("#")
        path = path.lstrip("./")
        target = self.site.doc_pages.get(path)
        if target is not None:
            if frag:
                resolved = self.site.anchor_target(frag, default_page=target)
                if resolved:
                    return self.p.u(resolved)
            return self.p.u(target)
        if path.startswith("reference/interviews/originals/"):
            iv = self.site.interview_by_file.get(os.path.basename(path))
            if iv:
                return self.p.u(iv.url)
        if path.endswith("/"):
            return TREE + path
        return blob_url(path) + (f"#{frag}" if frag else "")

    def _anchor(self, frag):
        resolved = self.site.anchor_target(frag)
        if resolved is None:
            return "#" + frag
        if self.same_page_anchors and resolved.startswith(self.p.path + "#"):
            return resolved[len(self.p.path):]
        if resolved == self.p.path:
            return "#top"
        return self.p.u(resolved)

    # ----------------------------------------------------------------- images
    def image(self, src):
        src = (src or "").strip()
        if src.startswith(("http://", "https://", "data:")):
            return src, None, None
        path = src.lstrip("./").split("#")[0]
        if not path.startswith("assets/images/"):
            return None, None, None
        rel = path[len("assets/images/"):]
        if not self.site.img.ensure(rel):
            return None, None, None
        return self.p.img(rel), None, blob_url(path), origin_attr(rel)

    # -------------------------------------------------------------- footnotes
    def footnote(self, num):
        if not self.footnote_page:
            return None
        if self.footnote_page == self.p.path:
            return f"#fn-{num}"
        return self.p.u(f"{self.footnote_page}#fn-{num}")


class AnchorStream:
    """Hands the renderer the document-wide anchor each heading had on GitHub."""

    def __init__(self, pairs):
        self.pairs = pairs
        self.i = 0

    def __call__(self, text):
        for j in range(self.i, len(self.pairs)):
            if self.pairs[j][0] == text:
                self.i = j + 1
                return self.pairs[j][1]
        return md.github_slug(text) or "section"


# ==================================================================== the site
class Site:
    def __init__(self, verbose=False):
        self.corpus = C.Corpus(ROOT)
        self.img = ImageSet(os.path.join(ROOT, "assets", "images"),
                            os.path.join(OUT, "assets", "img"),
                            "assets/img", verbose=verbose)
        self.verbose = verbose
        self.ref_sections = paginate(C.split_reference(self.corpus.reference))
        self._plan_reference()
        self._plan_about()
        self.interview_by_file = {iv.basename: iv for iv in self.corpus.interviews}
        self.doc_pages = {
            C.REF_NAME: "reference/index.html",
            C.ABOUT_NAME: "about/index.html",
            C.VERIFY_NAME: "verification.html",
            C.INT_INDEX_NAME: "interviews/source-index.html",
            "README.md": "index.html",
        }
        self.pages = []            # (path, title) for the sitemap

    # ------------------------------------------------------- reference layout
    def _plan_reference(self):
        """Assign every reference heading the anchor and page it lives on."""
        self.anchors = {}          # github anchor -> "page.html" or "page.html#anchor"
        self.ref_pairs = {}        # section slug -> [(heading text, anchor)]
        seen = {}

        def mk(text):
            a = md.github_slug(text) or "section"
            n = seen.get(a)
            seen[a] = 0 if n is None else n + 1
            return a if n is None else f"{a}-{seen[a]}"

        for sec in self.ref_sections:
            top = mk(sec.title)
            self.anchors[top] = sec.url
            pairs = []
            for line in sec.lines:
                m = re.match(r"^(#{1,6})\s+(.*?)\s*#*$", line)
                if not m:
                    continue
                text = m.group(2).strip()
                a = mk(text)
                pairs.append((text, a))
                self.anchors[a] = f"{sec.url}#{a}"
            self.ref_pairs[sec.slug] = pairs
        self.footnote_page = next(
            (s.url for s in self.ref_sections if s.token == "Footnotes"), None)
        # section number (e.g. "2.1") -> page#anchor, for item pages
        self.section_link = {}
        for tok, anchor in self.corpus.anchors.items():
            if anchor in self.anchors:
                self.section_link[tok] = self.anchors[anchor]

    def _plan_about(self):
        for b in self.corpus.tier_b:
            a = md.github_slug(f"{b['id']} {b['title']}")
            b["anchor"] = a
            self.anchors.setdefault(a, f"about/index.html#{a}")

    def anchor_target(self, frag, default_page=None):
        target = self.anchors.get(frag)
        if target:
            return target
        if default_page:
            return f"{default_page}#{frag}"
        return None

    # ------------------------------------------------------------ page writer
    def page(self, path, *, title, body, description="", nav=None, wide=False):
        p = P(self, path)
        self.pages.append(path)
        nav_html = "".join(
            f'<li><a href="{e(p.u(href))}"'
            f'{" aria-current=\"page\"" if key == nav else ""}>{e(label)}</a></li>'
            for key, href, label in NAV)
        desc = description or TAGLINE
        full_title = title if path == "index.html" else f"{md.plain(title)} · Donna Tartt"
        doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(md.plain(full_title))}</title>
<meta name="description" content="{e(md.plain(desc))[:300]}">
<meta property="og:title" content="{e(md.plain(full_title))}">
<meta property="og:description" content="{e(md.plain(desc))[:300]}">
<meta property="og:type" content="website">
<link rel="icon" href="{FAVICON}">
<link rel="stylesheet" href="{e(p.u('assets/site.css'))}">
</head>
<body id="top">
<a class="skip" href="#main">Skip to content</a>
<header class="masthead">
  <div class="masthead-in">
    <a class="brand" href="{e(p.u('index.html'))}">Donna Tartt
      <span class="brand-sub">A Collector's Reference</span></a>
    <nav class="topnav" aria-label="Sections"><ul>{nav_html}</ul></nav>
  </div>
</header>
<main id="main" class="wrap{'' if wide else ''}">
{body}
</main>
{self._footer(p)}
<script src="{e(p.u('assets/site.js'))}" defer></script>
</body>
</html>
"""
        write(path, doc)
        return p

    def _footer(self, p):
        def links(items):
            return "".join(f'<li><a href="{e(p.u(h))}">{e(t)}</a></li>' for h, t in items)

        return f"""<footer class="site">
  <div class="wrap">
    <div class="cols">
      <div><h3>The catalogue</h3><ul>{links([
          ("editions/index.html", "Editions"),
          ("signed/index.html", "Signed & limited copies"),
          ("press/index.html", "Press & ephemera"),
          ("about/index.html", "Items about Tartt (Tier B)")])}</ul></div>
      <div><h3>In her own words</h3><ul>{links([
          ("interviews/index.html", "Interview transcripts"),
          ("interviews/source-index.html", "Interview source index"),
          ("essays/index.html", "Essays & short fiction"),
          ("contributions/index.html", "Introductions & contributions")])}</ul></div>
      <div><h3>Apparatus</h3><ul>{links([
          ("reference/index.html", "The master reference"),
          ("sources.html", "Primary-source captures"),
          ("verification.html", "Verification report"),
          ("colophon.html", "About this site & how to cite")])}</ul></div>
      <div><h3>Repository</h3><ul>
          <li><a class="ext" target="_blank" rel="noopener" href="{REPO}">GitHub repository</a></li>
          <li><a class="ext" target="_blank" rel="noopener" href="{BLOB}AGENTS.md">AGENTS.md (ask an AI)</a></li>
          <li><a class="ext" target="_blank" rel="noopener" href="{BLOB}LICENSE">Licence</a></li>
      </ul></div>
    </div>
    <p class="colophon">Generated from the
      <a class="ext" target="_blank" rel="noopener" href="{REPO}">donna-tartt-research</a>
      database — the cover manifest, the master reference, the Tier B list, the interview
      transcripts and the primary-source captures. Original research and compilation are
      licensed CC BY-NC 4.0; quoted material and source captures remain the copyright of their
      owners, reproduced here for non-commercial research. Claims are cross-checked against
      primary sources where possible; corrections and open questions are recorded in the
      <a href="{e(p.u('verification.html'))}">verification report</a>.</p>
  </div>
</footer>"""


# =============================================================== page pieces
def page_head(eyebrow, title, dek="", crumbs_html=""):
    dek_html = f'<p class="dek">{dek}</p>' if dek else ""
    return (f'{crumbs_html}<div class="page-head"><p class="eyebrow">{e(eyebrow)}</p>'
            f"<h1>{title}</h1>{dek_html}</div>")


def crumbs(p, trail):
    bits = []
    for href, label in trail[:-1]:
        bits.append(f'<a href="{e(p.u(href))}">{e(label)}</a>')
    bits.append(e(trail[-1][1]))
    return '<p class="crumbs">' + "<span>/</span>".join(bits) + "</p>"


def tile(p, href, cover, label, sub="", flag=""):
    if cover and p.site.img.ensure(cover):
        frame = (f'<div class="frame"><img src="{e(p.img(cover, thumb=True))}" alt="" '
                 f'loading="lazy" decoding="async" {origin_attr(cover)}></div>')
    else:
        frame = '<div class="frame"><span class="nocover">no cover held</span></div>'
    sub_html = f'<span class="sub">{sub}</span>' if sub else ""
    flag_html = f'<span class="flag">{e(flag)}</span>' if flag else ""
    return (f'<a class="tile" href="{e(p.u(href))}">{frame}'
            f'<span class="label">{label}{sub_html}{flag_html}</span></a>')


def row(p, href, cover, title, sub="", right=""):
    if cover and p.site.img.ensure(cover):
        mini = (f'<span class="mini"><img src="{e(p.img(cover, thumb=True))}" alt="" '
                f'loading="lazy" {origin_attr(cover)}></span>')
    else:
        mini = '<span class="mini empty"></span>'
    sub_html = f'<span class="s">{sub}</span>' if sub else ""
    return (f'<a class="row" href="{e(p.u(href))}">{mini}'
            f'<span><span class="t">{title}</span>{sub_html}</span>'
            f'<span class="y">{e(right)}</span></a>')


def filterbar(chips, placeholder, total):
    chip_html = "".join(
        f'<button type="button" class="chip" data-chip data-group="{e(k)}" '
        f'aria-pressed="false">{e(label)}</button>' for k, label in chips)
    return f"""<div class="filterbar">
  <input type="search" data-filter-input placeholder="{e(placeholder)}" aria-label="{e(placeholder)}">
  <div class="chips">{chip_html}</div>
  <span class="filter-count" data-filter-count>{total} items</span>
</div>"""


def meta_table(pairs):
    body = "".join(f"<tr><th>{e(k)}</th><td>{v}</td></tr>" for k, v in pairs if v)
    return f'<table class="meta"><tbody>{body}</tbody></table>' if body else ""


def section_label(text):
    return f'<span class="section-label">{e(text)}</span>'


def citation_block(p, text, note=""):
    note_html = f"<p>{note}</p>" if note else ""
    return (f'<div class="provenance"><p><b>Cite this entry</b></p>'
            f'<p><code id="cite">{e(text)}</code></p>{note_html}'
            f'<p><button type="button" class="chip" data-copy="cite">Copy citation</button></p></div>')


# ============================================================= index builders
def catalogue_index(site, path, *, nav, eyebrow, title, dek, groups, chips,
                    style="gallery", intro="", description=""):
    """A filterable index page.

    `groups` = [(key, heading, note, [(filter attributes, card html), ...])].
    The filter attributes go on the grid cell or the list item itself, so a
    filtered-out entry takes its row divider with it.
    """
    p = P(site, path)
    total = sum(len(cards) for _, _, _, cards in groups)
    blocks = []
    for key, heading, note, cards in groups:
        if not cards:
            continue
        note_html = f'<span class="n">{e(note)}</span>' if note else ""
        cell = "div" if style == "gallery" else "li"
        inner = "".join(f"<{cell} {attrs}>{card}</{cell}>" for attrs, card in cards)
        wrap = (f'<div class="gallery wide">{inner}</div>' if style == "gallery"
                else f'<ul class="listing">{inner}</ul>')
        blocks.append(
            f'<section data-block><div class="group-head"><h2 id="{e(md.slug(heading))}">'
            f"{e(heading)}</h2>{note_html}</div>{wrap}</section>")
    body = (page_head(eyebrow, e(title), dek, crumbs(p, [("index.html", "Home"), ("", title)]))
            + (intro or "")
            + '<div data-filter-scope>'
            + filterbar(chips, "Search this list…", total)
            + "".join(blocks)
            + '<p class="empty-note" data-filter-empty hidden>Nothing matches that search.</p>'
            + "</div>")
    site.page(path, title=title, body=body, nav=nav, description=description or dek)
    return p


def item_cards(p, items, style="gallery"):
    """(filter attributes, card html) for each item, for `catalogue_index`."""
    out = []
    for it in items:
        label = md.inline(it.name, SiteRewriter(p))
        sub = " · ".join(x for x in (it.publisher,
                                     it.country if len(it.country) <= 14 else "",
                                     year_label(it.year)) if x)
        flag = ""
        if it.misattributed:
            flag = "misattributed — see entry"
        elif it.has_text:
            flag = "full text held"
        search = norm_search(it.search_blob())
        group = it.work if it.is_novel else it.site_section
        card = (tile(p, it.url, it.cover, label, e(sub), flag) if style == "gallery"
                else row(p, it.url, it.cover, label, e(sub), year_label(it.year)))
        out.append((f'data-search="{e(search)}" data-group="{e(group)}"', card))
    return out


# ------------------------------------------------------------------ item page
def item_page(site, it):
    p = P(site, it.url)
    rw = SiteRewriter(p)
    sec_name = SECTION_TITLE[it.site_section]
    title_html = md.inline(it.name, rw)

    # ---- cover
    if it.cover and site.img.ensure(it.cover):
        cover_html = (
            f'<figure class="cover"><a href="{e(blob_url("assets/images/" + it.cover))}" '
            f'class="plate-link" target="_blank" rel="noopener">'
            f'<img src="{e(p.img(it.cover))}" alt="Cover of {e(md.plain(it.name))}" '
            f'{origin_attr(it.cover)}></a>'
            f'<figcaption>{e(os.path.basename(it.cover))} — full resolution in the repository</figcaption>'
            "</figure>")
    else:
        note = ("No cover image is held for this entry."
                if it.status != "alias (shares cover)"
                else "Shares its cover with another entry.")
        cover_html = f'<div class="nocover-box">{e(note)}</div>'

    # ---- metadata
    ref_href = site.section_link.get(it.section)
    ref_cell = (f'<a href="{e(p.u(ref_href))}">§{e(it.section)} of the reference</a>'
                if ref_href else f"§{e(it.section)}")
    suspect = row_suspect(it)
    rows = [
        ("Work", e(it.work_title) + (f" ({C.WORK_YEAR[it.work]})" if it.work in C.WORK_YEAR else "")),
        ("Reference", ref_cell),
        ("Publisher", e(it.publisher) if not suspect else ""),
        ("Country", e(it.country) if not suspect and len(it.country) <= 14 else ""),
        ("Language", e(it.language) if not suspect and len(it.language) <= 14 else ""),
        ("Year", e(year_label(it.year)) if not suspect else ""),
        ("ISBN-13", f"<code>{e(it.isbn13)}</code>"
         if not suspect and isbn_ok(it.isbn13) else ""),
        ("ISBN-10", f"<code>{e(it.isbn10)}</code>"
         if not suspect and isbn_ok(it.isbn10) else ""),
        ("Cover image", e(it.status)),
    ]

    # ---- actions
    actions = []
    if ref_href:
        actions.append(f'<a class="btn primary" href="{e(p.u(ref_href))}">Full entry in the reference</a>')
    for url in it.originals[:3]:
        actions.append(f'<a class="btn ext" target="_blank" rel="noopener" href="{e(url)}">'
                       f'Original: {e(C.host_of(url))}</a>')
    if it.pdf:
        actions.append(f'<a class="btn" target="_blank" rel="noopener" '
                       f'href="{e(blob_url(C.EXCERPT_REL + "/" + it.pdf))}">Excerpt (PDF)</a>')
    actions.append(f'<a class="btn" target="_blank" rel="noopener" '
                   f'href="{BLOB}data/cover_manifest.csv">Manifest row</a>')

    head = f"""<div class="item-head">
  <div>{cover_html}</div>
  <div>
    <p class="item-kicker"><code>{e(it.id)}</code> · {e(it.work_title)} · §{e(it.section)}</p>
    <h1 class="item-title">{title_html}</h1>
    {meta_table(rows)}
    <div class="actions">{"".join(actions)}</div>
  </div>
</div>"""

    parts = [crumbs(p, [("index.html", "Home"),
                        (f"{it.site_section}/index.html", sec_name),
                        ("", it.id)]), head]

    if suspect:
        parts.append(
            '<div class="callout"><p><b>Malformed manifest row.</b> This entry\'s row in '
            '<code>data/cover_manifest.csv</code> contains an unescaped comma, which shifts its '
            'later columns out of their fields. The fields that cannot be trusted are left blank '
            'above rather than printed as fact — read the reference section for the '
            'authoritative detail.</p></div>')

    if it.misattributed:
        parts.append('<div class="callout"><p><b>Misattribution.</b> The manifest records this '
                     'item as <em>not by Tartt</em>. It is kept in the catalogue so the '
                     'misidentification stays documented rather than resurfacing; see the '
                     'reference section above for what the item actually is.</p></div>')

    # ---- full text / excerpt held in the repository
    body_html, body_src = it.body_html(rw)
    if body_html:
        src_url = it.fulltext_source_url()
        src_note = (f' Retrieved from <a class="ext" target="_blank" rel="noopener" '
                    f'href="{e(src_url)}">{e(C.host_of(src_url))}</a>.' if src_url else "")
        parts.append(section_label("Text held in this archive"))
        parts.append(f'<div class="provenance"><p>Reproduced from '
                     f'<a target="_blank" rel="noopener" href="{e(blob_url(body_src))}">'
                     f"<code>{e(body_src)}</code></a> in the repository.{src_note} "
                     "Quoted for non-commercial research; rights remain with the "
                     "original publisher.</p></div>")
        parts.append(f'<div class="fulltext">{body_html}</div>')

    # ---- page scans
    if it.scans:
        parts.append(section_label("Page scans"))
        tiles = []
        for rel in it.scans:
            if not site.img.ensure(rel):
                continue
            label = e(os.path.basename(rel))
            tiles.append(
                f'<a class="tile" href="{e(p.img(rel))}">'
                f'<span class="frame"><img src="{e(p.img(rel, thumb=True))}" alt="{label}" '
                f'loading="lazy" {origin_attr(rel)}></span>'
                f'<span class="label">{label}</span></a>')
        parts.append(f'<div class="gallery">{"".join(tiles)}</div>')
        parts.append(
            f'<p class="small">Each page opens a readable copy; the full-resolution scans are '
            f'under <a target="_blank" rel="noopener" href="{TREE}assets/images/scans">'
            f'<code>assets/images/scans/</code></a> in the repository.</p>')

    # ---- primary sources
    parts.append(sources_section(p, it))

    cite_bits = [f'"{md.plain(it.name)}"']
    if it.publisher and not suspect:
        cite_bits.append(it.publisher)
    if year_label(it.year) and not suspect:
        cite_bits.append(year_label(it.year))
    cite = (", ".join(cite_bits) + f". Donna Tartt — A Collector's Reference, §{it.section} "
            f"({it.id}). {REPO}")
    parts.append(citation_block(p, cite))

    site.page(it.url, title=md.plain(it.name), body="".join(parts), nav=it.site_section,
              description=f"{md.plain(it.name)} — {it.work_title}. "
                          f"{it.publisher} {it.year}. Catalogue entry {it.id}.")


def sources_section(p, it):
    """The held captures and canonical URLs cited for this entry's section."""
    lis = []
    for rel, base in sorted(it.sources.items(), key=lambda kv: kv[1].lower()):
        kind = it.corpus.source_kind(base)
        lis.append(f'<li><a target="_blank" rel="noopener" href="{e(blob_url(rel))}">'
                   f"{e(C.prettify(base))}</a>"
                   f'<span class="kind">{e(kind)}</span></li>')
    for url in it.originals:
        lis.append(f'<li><a class="ext" target="_blank" rel="noopener" href="{e(url)}">'
                   f"{e(url)}</a><span class=\"kind\">original URL</span></li>")
    if not lis:
        return ("" + section_label("Primary sources")
                + '<p class="small">No capture is filed against this entry on its own; the '
                  'citations for its reference section carry the evidence.</p>')
    return (section_label("Primary sources")
            + '<p class="small">Saved captures and canonical URLs cited for §'
            + e(it.section) + ' of the reference. Files open in the repository.</p>'
            + f'<ul class="sources">{"".join(lis)}</ul>')


# -------------------------------------------------------------- interviews
def interview_page(site, iv):
    p = P(site, iv.url)
    rw = SiteRewriter(p)
    fields = "".join(
        f"<tr><th>{e(k)}</th><td>{md.inline(v, rw)}</td></tr>" for k, v in iv.header.ordered())
    note = f"<p>{md.inline(iv.header.note, rw)}</p>" if iv.header.note else ""
    url = iv.header.url()
    actions = []
    if url:
        actions.append(f'<a class="btn primary ext" target="_blank" rel="noopener" '
                       f'href="{e(url)}">Original publication</a>')
    actions.append(f'<a class="btn" target="_blank" rel="noopener" '
                   f'href="{e(blob_url(iv.repo_path))}">Transcript in the repository</a>')
    actions.append(f'<a class="btn" href="{e(p.u("interviews/source-index.html"))}">Interview index</a>')

    body_md = iv.header.body or ""
    transcript = md.render(body_md, rw, heading_level=2) if body_md.strip() else (
        '<p class="empty-note">This entry records the interview\'s provenance; '
        'the transcript text is not held in the repository.</p>')

    sub = " · ".join(x for x in (md.plain(iv.outlet), md.plain(iv.interviewer),
                                 md.plain(iv.date)) if x)
    parts = [
        crumbs(p, [("index.html", "Home"), ("interviews/index.html", "Interviews"), ("", iv.year)]),
        f'<div class="page-head"><p class="eyebrow">Interview transcript</p>'
        f"<h1>{md.inline(iv.title, rw)}</h1>"
        f'<p class="dek">{e(sub)}</p></div>',
        f'<div class="provenance"><p><b>Provenance</b></p>'
        f'<table class="meta"><tbody>{fields}</tbody></table>{note}</div>',
        f'<div class="actions">{"".join(actions)}</div>',
        f'<div class="transcript">{transcript}</div>',
    ]
    cite = (f'"{md.plain(iv.title)}" — Donna Tartt interviewed'
            + (f" by {iv.interviewer}" if iv.interviewer else "")
            + (f", {iv.outlet}" if iv.outlet else "")
            + (f", {iv.date}" if iv.date else "")
            + f". Transcript: {blob_url(iv.repo_path)}")
    parts.append(citation_block(
        p, cite, "Quoted words are Tartt's own as printed by the original outlet; "
                 "surrounding narration is the interviewer's."))
    site.page(iv.url, title=md.plain(iv.title), body="".join(parts), nav="interviews",
              description=f"Donna Tartt interview — {sub}")


def extra_page(site, ex):
    p = P(site, ex.url)
    rw = SiteRewriter(p)
    kind = "Interview" if ex.kind == "interview" else "Tartt byline"
    actions = []
    if ex.source_url:
        actions.append(f'<a class="btn primary ext" target="_blank" rel="noopener" '
                       f'href="{e(ex.source_url)}">Original publication</a>')
    actions.append(f'<a class="btn" target="_blank" rel="noopener" '
                   f'href="{e(blob_url(ex.repo_path))}">Text in the repository</a>')
    parts = [
        crumbs(p, [("index.html", "Home"), ("interviews/index.html", "Interviews"), ("", ex.id)]),
        f'<div class="page-head"><p class="eyebrow">{e(kind)} · full text held</p>'
        f"<h1>{e(md.plain(ex.title))}</h1>"
        + (f'<p class="dek">{md.inline(ex.note, rw)}</p>' if ex.note else "")
        + "</div>",
        f'<div class="actions">{"".join(actions)}</div>',
        f'<div class="transcript">{md.render(ex.body_md, rw, heading_level=2)}</div>',
        citation_block(p, f"{md.plain(ex.title)} ({ex.id}). Text: {blob_url(ex.repo_path)}"),
    ]
    site.page(ex.url, title=md.plain(ex.title), body="".join(parts), nav="interviews",
              description=f"Donna Tartt — {md.plain(ex.title)}")


# --------------------------------------------------------------- doc pages
def doc_page(site, path, repo_rel, *, nav, eyebrow, title, dek, description="",
             heading_level=2, sidebar_title="On this page"):
    """Render a whole repository Markdown document as one page, with a mini TOC."""
    p = P(site, path)
    rw = SiteRewriter(p, same_page_anchors=True)
    text = C.read(ROOT, repo_rel)
    _, body = md.split_front_matter(text)
    toc = []
    rendered = md.render(dedupe_captions(body), rw, heading_level=heading_level,
                         heading_sink=lambda lvl, t, a: toc.append((lvl, t, a)))
    links = "".join(
        f'<li{" class=\"sub\"" if lvl > 2 else ""}><a href="#{e(a)}">{e(md.plain(t))}</a></li>'
        for lvl, t, a in toc if lvl <= 3)
    side = (f'<aside class="ref-side"><h2>{e(sidebar_title)}</h2><ul>{links}</ul></aside>'
            if links else "")
    body_html = f"""{page_head(eyebrow, e(title), dek,
                               crumbs(p, [("index.html", "Home"), ("", title)]))}
<p class="small">Rendered from <a target="_blank" rel="noopener" href="{e(blob_url(repo_rel))}">
<code>{e(repo_rel)}</code></a> in the repository — the file is the source of record.</p>
<div class="ref-layout">{side}<div class="ref-body prose-wide">{rendered}</div></div>"""
    site.page(path, title=title, body=body_html, nav=nav, description=description or dek)


# =================================================================== builders
def build_home(site, c):
    p = P(site, "index.html")
    covers = []
    want = [("TSH", "2.1"), ("TLF", "3.1"), ("TG", "4.1"), ("TG", "4.2")]
    for work, sec in want:
        it = next((i for i in c.items if i.work == work and i.section == sec and i.cover), None)
        if it is None:
            it = next((i for i in c.items if i.work == work and i.cover), None)
        if it and it not in covers:
            covers.append(it)
    shelf = "".join(
        f'<a href="{e(p.u(it.url))}" title="{e(md.plain(it.name))}">'
        f'<img src="{e(p.img(it.cover))}" alt="{e(md.plain(it.name))}" '
        f'{origin_attr(it.cover)}></a>'
        for it in covers if site.img.ensure(it.cover))

    n_cover = sum(1 for i in c.items if i.status == "have")
    n_fn = len(re.findall(r"(?m)^\d+\.\s", c.sec_body.get("Footnotes", "")
                          or C.read(ROOT, C.REF_NAME).split("## Footnotes")[-1]))
    stats = [
        (len(c.items), "editions catalogued"),
        (n_cover, "with cover images"),
        (len(c.interviews) + len([x for x in c.extras if x.kind == "interview"]),
         "interview texts"),
        (len(C.EMBED) + len(C.PDF_LINK), "works excerpted"),
        (len(c.src_by_base), "source files held"),
        (len(c.tier_b), "Tier B items"),
    ]
    stats_html = "".join(f"<div><b>{n}</b><span>{e(lbl)}</span></div>" for n, lbl in stats)

    def card(href, count, title, text):
        return (f'<a class="card" href="{e(p.u(href))}">'
                f'<span class="count">{e(count)}</span><h3>{e(title)}</h3><p>{text}</p></a>')

    n_signed = len(c.signed_items())
    n_ess = len([i for i in c.items if i.site_section == "essays"])
    n_con = len([i for i in c.items if i.site_section == "contributions"])
    n_press = len([i for i in c.items if i.site_section == "press"])
    n_ed = len([i for i in c.items if i.is_novel])

    cards = "".join([
        card("editions/index.html", f"{n_ed} entries", "Editions",
             "Every edition of <em>The Secret History</em>, <em>The Little Friend</em> and "
             "<em>The Goldfinch</em> — US and UK firsts, proofs and ARCs, foreign-language "
             "firsts, audiobooks, large-print and e-books."),
        card("signed/index.html", f"{n_signed} entries", "Signed copies",
             "Signed, numbered, lettered and deluxe limited editions, with the authentication "
             "apparatus: signature characteristics, the ink-colour-by-signing-programme table "
             "and forgery red flags."),
        card("essays/index.html", f"{n_ess} entries", "Essays & short fiction",
             "Her short stories and nonfiction — <em>Sleepytown</em>, <em>Basketball Season</em>, "
             "<em>Team Spirit</em>, the Harper's essays — with the text itself where the archive "
             "holds it."),
        card("contributions/index.html", f"{n_con} entries", "Contributions",
             "Introductions, forewords, afterwords, translations, catalogue essays and the "
             "audiobooks she narrated, with her contribution excerpted where it is held."),
        card("interviews/index.html",
             f"{len(c.interviews)} transcripts", "Interviews",
             "Transcripts of on-record interviews in Tartt's own voice, each with full "
             "provenance — outlet, interviewer, date and original URL."),
        card("reference/index.html", "16 chapters", "The master reference",
             "The long-form reference the rest of the site indexes: points of issue, print runs, "
             "auction history, translator cross-reference and 108 numbered footnotes."),
    ])

    quotes = []
    for iv in list(reversed(c.interviews))[:4]:
        sub = " · ".join(x for x in (md.plain(iv.outlet), md.plain(iv.interviewer)) if x)
        quotes.append(f'<li>{row(p, iv.url, None, e(md.plain(iv.title)), e(sub),
                                 short_date(iv.date) or iv.year)}</li>')

    body = f"""<div class="hero">
  <p class="eyebrow">A research database</p>
  <h1>Donna Tartt</h1>
  <p class="dek">{TAGLINE}</p>
  {FLOURISH}
  <div class="shelf">{shelf}</div>
</div>
<div class="stats">{stats_html}</div>
<h2>Browse the database</h2>
<div class="cards">{cards}</div>
<div class="group-head"><h2>Her own words</h2>
  <a class="more" href="{e(p.u('interviews/index.html'))}">All interviews →</a></div>
<ul class="listing">{"".join(quotes)}</ul>
<div class="callout note"><p><b>How to read this site.</b> Tier A is work <em>by</em> Tartt —
  the editions, essays, contributions and interviews. Tier B is material
  <a href="{e(p.u('about/index.html'))}">about</a> her, kept separate on purpose. Quotations
  inside a transcript or an excerpt are Tartt's; descriptive prose in the reference is the
  compiler's. Claims are cross-checked against primary sources where possible, and anything
  single-sourced or unsettled is logged in the
  <a href="{e(p.u('verification.html'))}">verification report</a>.</p></div>
<div class="callout"><p><b>Asking an AI instead of reading?</b> The repository ships an
  <a class="ext" target="_blank" rel="noopener" href="{BLOB}AGENTS.md">AGENTS.md</a> that tells an
  assistant how to search this corpus and answer <em>with citations</em> rather than from memory.</p></div>"""
    site.page("index.html", title="Donna Tartt — A Collector's Reference", body=body,
              description=TAGLINE)


def build_editions(site, c):
    p = P(site, "editions/index.html")
    groups = []
    for work in C.NOVELS:
        items = c.group(work)
        groups.append((work, f"{C.WORK_TITLE[work]} ({C.WORK_YEAR[work]})",
                       f"{len(items)} entries · §{C.NOVEL_SECTION[work]}",
                       item_cards(p, items)))
    catalogue_index(
        site, "editions/index.html", nav="editions", eyebrow="Tier A · the novels",
        title="Editions",
        dek="Every catalogued edition of the three novels: US and UK firsts and their points of "
            "issue, proofs and advance copies, signed and limited issues, foreign-language "
            "firsts, audiobooks, large-print and e-book editions.",
        groups=groups,
        chips=[(w, C.WORK_TITLE[w]) for w in C.NOVELS])


SIGNED_RE = re.compile(r"\bsign|limited|lettered|numbered|inscrib|deluxe|indiespensable",
                       re.I)


def build_signed(site, c):
    p = P(site, "signed/index.html")
    # `Corpus.signed_items` looks only at the novels and the contributions; the
    # signed Lenox Hill chapbook sits under Press and belongs here too.
    items = [it for it in c.items if SIGNED_RE.search(it.name)]
    by_work = {}
    for it in items:
        by_work.setdefault(it.work, []).append(it)
    groups = []
    for work in list(C.NOVELS) + ["Contributions", "Press"]:
        got = sorted(by_work.get(work, []), key=lambda i: C.natkey(i.section))
        if got:
            groups.append((work, C.WORK_TITLE.get(work, work), f"{len(got)} entries",
                           item_cards(p, got)))
    auth = site.section_link.get("9", "reference/index.html")
    ink = site.section_link.get("9.2", auth)
    forge = site.section_link.get("9.4", auth)
    intro = f"""<div class="callout note"><p><b>Before you buy.</b> The reference's authentication
chapter is the part of this database most worth reading in full: the
<a href="{e(p.u(ink))}">ink-colour-by-signing-programme table</a> dates a signature from the colour
it was signed in, <a href="{e(p.u(auth))}">§9</a> sets out the signature characteristics by era and
the standard inscription phrases, and
<a href="{e(p.u(forge))}">the forgery red flags</a> list what a suspect copy tends to get wrong.</p>
</div>"""
    catalogue_index(
        site, "signed/index.html", nav="signed", eyebrow="Tier A · signed & limited",
        title="Signed copies",
        dek="Signed, inscribed, numbered, lettered and deluxe limited issues catalogued across "
            "the three novels and her contributions — each one linking to its full entry, its "
            "limitation and whatever provenance the archive holds.",
        groups=groups, chips=[(k, C.WORK_TITLE.get(k, k)) for k, _, _, _ in groups],
        intro=intro)


def build_essays(site, c):
    p = P(site, "essays/index.html")
    groups = []
    for work, heading, sec in (("Short Fiction", "Short fiction", "5"),
                               ("Nonfiction", "Nonfiction & essays", "6")):
        items = c.group(work)
        groups.append((work, heading, f"{len(items)} entries · §{sec}",
                       item_cards(p, items, style="listing")))
    catalogue_index(
        site, "essays/index.html", nav="essays", eyebrow="Tier A · her own writing",
        title="Essays & short fiction", style="listing",
        dek="Tartt's short stories and nonfiction as first published — magazine by magazine, with "
            "the full text reproduced where the archive holds it and a link to the original "
            "publication where it does not.",
        groups=groups,
        chips=[("Short Fiction", "Short fiction"), ("Nonfiction", "Nonfiction")])


def build_contributions(site, c):
    p = P(site, "contributions/index.html")
    items = c.group("Contributions")
    held = [i for i in items if i.has_text or i.pdf]
    rest = [i for i in items if not (i.has_text or i.pdf)]
    groups = [
        ("contributions", "With Tartt's contribution held here",
         f"{len(held)} entries", item_cards(p, held)),
        ("contributions", "Catalogued, contribution not reproduced",
         f"{len(rest)} entries", item_cards(p, rest)),
    ]
    intro = f"""<div class="callout note"><p><b>What is reproduced here.</b> The books Tartt
contributed to are other people's copyrighted work, so only her own contribution is extracted into
this archive — the foreword, the essay, the translation, the poem. The complete books are held in a
separate private archive and are cited here by publication and ISBN. See
<a class="ext" target="_blank" rel="noopener" href="{BLOB}ARCHITECTURE.md">ARCHITECTURE.md</a>.</p>
</div>"""
    catalogue_index(
        site, "contributions/index.html", nav="contributions",
        eyebrow="Tier A · §7", title="Introductions & contributions",
        dek="Forewords, afterwords, introductions, translations, catalogue essays, anthology "
            "pieces and the audiobooks Tartt narrated — including the entries kept on record "
            "precisely because they are misattributions.",
        groups=groups, chips=[], intro=intro)


def build_press(site, c):
    p = P(site, "press/index.html")
    items = c.group("Press")
    catalogue_index(
        site, "press/index.html", nav="press", eyebrow="Tier A · §8",
        title="Press & ephemera",
        dek="The launch-era press, the Lenox Hill chapbook programme and the publisher ephemera "
            "that document how the books were sold — catalogued as artifacts, with the captures "
            "that evidence them.",
        groups=[("press", "Press & ephemera", f"{len(items)} entries",
                 item_cards(p, items, style="listing"))],
        chips=[], style="listing")


def build_about(site, c):
    path = "about/index.html"
    p = P(site, path)
    rw = SiteRewriter(p, same_page_anchors=True)
    blocks = []
    nav_links = []
    for b in c.tier_b:
        cover = b["cover"]
        if cover and site.img.ensure(cover):
            fig = (f'<figure class="cover"><a class="plate-link" target="_blank" rel="noopener" '
                   f'href="{e(blob_url("assets/images/" + cover))}">'
                   f'<img src="{e(p.img(cover))}" alt="{e(md.plain(b["title"]))}" '
                   f'{origin_attr(cover)}></a></figure>')
        else:
            fig = '<div class="nocover-box">No cover image held</div>'
        nav_links.append(f'<li><a href="#{e(b["anchor"])}">{e(b["id"])} — '
                         f"{e(md.plain(b['title']))}</a></li>")
        blocks.append(f"""<section class="item-head" id="{e(b['anchor'])}">
  <div>{fig}</div>
  <div><p class="item-kicker"><code>{e(b['id'])}</code> · Tier B</p>
    <h2 class="item-title">{md.inline(b['title'], rw)}
      <a class="anchor" href="#{e(b['anchor'])}" aria-label="Permalink">#</a></h2>
    {md.render(dedupe_captions(b['body']), rw, heading_level=3)}</div>
</section>""")
    side = f'<aside class="ref-side"><h2>Tier B items</h2><ul>{"".join(nav_links)}</ul></aside>'
    body = (page_head("Tier B · about Tartt", "Items about Donna Tartt",
                      "Material in which Tartt is the subject rather than the author — magazine "
                      "profiles, signed promotional ephemera, cover-blurb mentions. Kept apart "
                      "from Tier A so that what she wrote is never conflated with what was "
                      "written about her.",
                      crumbs(p, [("index.html", "Home"), ("", "About Tartt")]))
            + f'<p class="small">Rendered from <a target="_blank" rel="noopener" '
              f'href="{e(blob_url(C.ABOUT_NAME))}"><code>{e(C.ABOUT_NAME)}</code></a>.</p>'
            + f'<div class="ref-layout">{side}<div class="ref-body">{"".join(blocks)}</div></div>')
    site.page(path, title="Items about Donna Tartt", body=body, nav="about",
              description="Tier B: magazine profiles, signed posters and other items about "
                          "Donna Tartt that she did not write.")


def build_interviews(site, c):
    path = "interviews/index.html"
    p = P(site, path)
    for iv in c.interviews:
        interview_page(site, iv)
    for ex in c.extras:
        extra_page(site, ex)

    decades = {}
    for iv in c.interviews:
        key = (iv.year[:3] + "0s") if iv.year else "undated"
        decades.setdefault(key, []).append(iv)
    groups = []
    for key in sorted(decades):
        rows_html = []
        for iv in sorted(decades[key], key=lambda x: x.stem):
            sub = " · ".join(x for x in (md.plain(iv.outlet),
                                        md.plain(iv.interviewer)) if x)
            search = norm_search(iv.search_blob())
            rows_html.append((
                f'data-search="{e(search)}" data-group="{e(key)}"',
                row(p, iv.url, None, e(md.plain(iv.title)), e(sub),
                    short_date(iv.date) or iv.year)))
        groups.append((key, key, plural(len(decades[key]), "transcript"), rows_html))

    extras_rows = []
    for ex in c.extras:
        search = norm_search(ex.search_blob())
        label = "Tartt byline" if ex.kind == "byline" else "Interview"
        extras_rows.append((
            f'data-search="{e(search)}" data-group="extra"',
            row(p, ex.url, None, e(md.plain(ex.title)), e(label), ex.year)))
    if extras_rows:
        groups.append(("extra", "Further full texts held",
                       plural(len(extras_rows), "item"), extras_rows))

    intro = f"""<div class="callout note"><p><b>Scope.</b> These are the interviews whose text is
captured to disk. The <a href="{e(p.u('interviews/source-index.html'))}">interview source index</a>
maps <em>every</em> known Tartt interview — print, television, radio, podcast and public event —
with provenance and capture status, including the ones that exist only as a citation.</p></div>"""

    catalogue_index(
        site, path, nav="interviews", eyebrow="Tier A · her own voice", title="Interviews",
        dek="Transcripts of on-record interviews in which Tartt herself speaks, each page "
            "carrying the full provenance block — outlet, interviewer, date, pagination and the "
            "original URL — so any quotation can be traced back to where it was printed.",
        groups=groups, style="listing", intro=intro,
        chips=[(k, "Other texts" if k == "extra" else k) for k, _, _, _ in groups])

    doc_page(site, "interviews/source-index.html", C.INT_INDEX_NAME, nav="interviews",
             eyebrow="Apparatus", title="Interview source index",
             dek="Every known Tartt interview and byline, with provenance and capture status.",
             sidebar_title="Sections")


def chapter_gist(sec):
    """A one-line orientation for a reference chapter, drawn from the chapter.

    Its own subsection headings make the best summary and can never go stale;
    chapters that have none fall back to their first line of prose (skipping
    plate captions and the bibliographic boilerplate).
    """
    subs = [md.plain(re.sub(r"^###+\s+", "", l)).strip()
            for l in sec.lines if re.match(r"^###+\s+\S", l)]
    if subs:
        shown = " · ".join(_clip(s, 46) for s in subs[:3])
        if len(subs) > 3:
            shown += f" · +{len(subs) - 3} more"
        return shown
    skip = re.compile(r"^(Figure|Fig\.|Canonical URL|Article|Photo|Cover|Source|Note)\b", re.I)
    for line in sec.lines:
        t = line.strip()
        if (not t or t.startswith(("#", "|", "!", ">", "---", "**")) or skip.match(t)
                or re.match(r"^[-*]\s", t)):
            continue
        gist = md.plain(t)
        if len(gist) > 40:
            return gist[:118].rsplit(" ", 1)[0] + "…" if len(gist) > 120 else gist
    return ""


def build_reference(site, c):
    secs = site.ref_sections
    p_index = P(site, "reference/index.html")

    side_items = "".join(
        f'<li><a href="{e(p_index.u(s.url))}">{e(md.plain(s.title))}</a></li>' for s in secs)
    body = (page_head("The master reference", "Donna Tartt — A Collector's Reference",
                      "The long-form document behind the catalogue, split into chapters. "
                      "Headings, tables, plates and all 108 numbered footnotes are preserved; "
                      "every link resolves either to another chapter or to the artifact in the "
                      "repository.",
                      crumbs(p_index, [("index.html", "Home"), ("", "Reference")]))
            + f'<p class="small">Rendered from <a target="_blank" rel="noopener" '
              f'href="{e(blob_url(C.REF_NAME))}"><code>{e(C.REF_NAME)}</code></a> — '
              "the file is the source of record.</p>"
            + '<ul class="listing">'
            + "".join(
                f'<li><a class="row" href="{e(p_index.u(s.url))}">'
                f'<span class="mini empty"></span>'
                f'<span><span class="t">{e(md.plain(s.title))}</span>'
                f'<span class="s">{e(chapter_gist(s))}</span></span>'
                f'<span class="y">§{e(s.token)}</span></a></li>' for s in secs)
            + "</ul>")
    site.page("reference/index.html", title="The master reference", body=body, nav="reference",
              description="Chapter index of the Donna Tartt collector's reference.")

    for i, sec in enumerate(secs):
        p = P(site, sec.url)
        rw = SiteRewriter(p, same_page_anchors=True, footnote_page=site.footnote_page)
        stream = AnchorStream(site.ref_pairs[sec.slug])
        rendered = md.render(dedupe_captions(sec.body_md), rw, heading_level=2,
                             anchor_fn=stream,
                             linkify_footnotes=True,
                             footnote_ids=(sec.token == "Footnotes"))
        sub = "".join(
            f'<li class="sub"><a href="#{e(a)}">{e(md.plain(t))}</a></li>'
            for t, a in site.ref_pairs[sec.slug][:80]
            if a and len(md.plain(t)) < 110)
        nav_list = []
        for s in secs:
            cur = ' aria-current="page"' if s is sec else ""
            nav_list.append(f'<li><a href="{e(p.u(s.url))}"{cur}>{e(md.plain(s.title))}</a></li>')
            if s is sec and sub:
                nav_list.append(f"</ul><ul>{sub}</ul><ul>")
        side = (f'<aside class="ref-side"><h2>The reference</h2>'
                f'<ul>{"".join(nav_list)}</ul></aside>')
        pager = []
        if i:
            pager.append(f'<a href="{e(p.u(secs[i-1].url))}"><span class="lbl">Previous</span>'
                         f"{e(md.plain(secs[i-1].title))}</a>")
        if i + 1 < len(secs):
            pager.append(f'<a class="next" href="{e(p.u(secs[i+1].url))}">'
                         f'<span class="lbl">Next</span>{e(md.plain(secs[i+1].title))}</a>')
        body = (crumbs(p, [("index.html", "Home"), ("reference/index.html", "Reference"),
                           ("", f"§{sec.token}")])
                + f'<div class="page-head"><p class="eyebrow">The master reference</p>'
                  f"<h1>{e(md.plain(sec.title))}</h1></div>"
                + f'<div class="ref-layout">{side}<div class="ref-body">{rendered}'
                + (f'<nav class="pager">{"".join(pager)}</nav>' if pager else "")
                + "</div></div>")
        site.page(sec.url, title=md.plain(sec.title), body=body, nav="reference",
                  description=f"{md.plain(sec.title)} — Donna Tartt: A Collector's Reference.")


def build_sources(site, c):
    """An index of every primary-source capture held in the repository."""
    path = "sources.html"
    p = P(site, path)
    buckets = {}
    for base, rel in c.src_by_base.items():
        folder = os.path.dirname(rel)
        buckets.setdefault(folder, []).append((base, rel))
    labels = {
        "assets/sources/archive": "Dealer & press captures (S###)",
        "assets/sources/archive/wayback": "Wayback Machine snapshots",
        "assets/sources/archive/excerpts": "Excerpts of Tartt's own contributions",
        "assets/sources/press_primary": "Primary press PDFs",
        "assets/sources/auction_records": "Auction records",
        "assets/sources/editions_foreign": "Foreign publishers & library catalogues",
        "assets/sources/ebay": "Marketplace captures",
        "assets/sources/misc_web_saves": "Dealer & aggregator saves",
        "assets/articles": "Newspaper article PDFs",
    }
    blocks = []
    total = 0
    for folder in sorted(buckets, key=lambda f: (labels.get(f) is None, f)):
        files = sorted(buckets[folder], key=lambda kv: kv[0].lower())
        total += len(files)
        lis = "".join(
            f'<li data-search="{e(norm_search(base, folder))}" data-group="{e(folder)}">'
            f'<a target="_blank" rel="noopener" href="{e(blob_url(rel))}">{e(C.prettify(base))}</a>'
            f'<span class="kind">{e(c.source_kind(base))}</span></li>' for base, rel in files)
        blocks.append(f'<section data-block><div class="group-head">'
                      f'<h2>{e(labels.get(folder, folder))}</h2>'
                      f'<span class="n">{len(files)} files · <code>{e(folder)}/</code></span>'
                      f'</div><ul class="sources">{lis}</ul></section>')
    body = (page_head("Apparatus", "Primary-source captures",
                      "Every saved artifact behind the catalogue: dealer and press pages captured "
                      "to HTML, auction lot records, newspaper PDFs, foreign-publisher and library "
                      "catalogue pages, and the excerpts of Tartt's own contributions. Each link "
                      "opens the file in the repository.",
                      crumbs(p, [("index.html", "Home"), ("", "Sources")]))
            + '<div class="callout note"><p><b>Why these exist.</b> Dealer listings, auction pages '
              'and newspaper archives rot. Each capture is the state of the page on the day the '
              'claim was verified, so a citation here stays checkable after the original URL '
              'stops resolving. <code>.webarchive</code> files are Safari page bundles — download '
              'rather than preview them.</p></div>'
            + '<div data-filter-scope>'
            + filterbar([], "Search captures by filename…", total)
            + "".join(blocks)
            + '<p class="empty-note" data-filter-empty hidden>Nothing matches that search.</p>'
            + "</div>")
    site.page(path, title="Primary-source captures", body=body, nav=None,
              description="Index of the saved primary-source captures behind the Donna Tartt "
                          "research database.")


def build_colophon(site, c):
    path = "colophon.html"
    p = P(site, path)
    body = (page_head("Colophon", e("About this site & how to cite it"),
                      "What this database is, what it deliberately leaves out, and how to quote "
                      "from it.",
                      crumbs(p, [("index.html", "Home"), ("", "Colophon")]))
            + f"""<div class="prose">
<h2 id="what">What this is</h2>
<p>A sourced public reference documenting every published edition, signed copy, contribution and
notable artifact connected to the American novelist Donna Tartt (b. 1963). It is organised in two
tiers: <strong>Tier A</strong> is work by Tartt — the novels and their editions, her short fiction
and essays, her introductions and contributions, the audiobooks she narrated, and her on-record
interviews. <strong>Tier B</strong> is material <a href="{e(p.u('about/index.html'))}">about</a>
her that she did not write. The distinction is kept rigidly, because conflating the two is how most
misinformation about Tartt starts.</p>

<h2 id="sources">Sources and evidence</h2>
<p>Every page on this site is generated from files in the repository: the cover manifest
(<code>data/cover_manifest.csv</code>), the master reference, the Tier B list, the interview
transcripts, and the captures under <code>assets/</code>. Nothing is written for the website that
is not already in the database. Cover images are republished here as downscaled derivatives — each
plate links to the full-resolution original in the repository. Captures, PDFs and transcripts are
cited by a link to the file itself.</p>

<h2 id="limits">What is not here</h2>
<p>One category is held privately: full-book scans of the works Tartt <em>contributed</em> to. Only
her own contribution is relevant and that is excerpted into the public repository; the complete
copyrighted books are not redistributed. They are cited by publication and ISBN instead.</p>
<p>Claims are cross-checked against primary sources where possible. Documented corrections, and any
entries that remain single-sourced or unsettled, are recorded in the
<a href="{e(p.u('verification.html'))}">verification report</a> — read it before treating a lone
entry as settled. Per-edition caveats and points of issue sit in the relevant chapter of the
<a href="{e(p.u('reference/index.html'))}">reference</a>.</p>

<h2 id="cite">How to cite</h2>
<p>Cite the underlying artifact, not this website, wherever the artifact is named. Each item page
carries a ready-made citation with its catalogue ID and reference section; interview pages carry
the outlet, interviewer, date and original URL. For the database as a whole:</p>
<div class="provenance"><p><code id="cite-database">Donna Tartt — A Collector's Reference
(research database), {time.strftime('%Y')}. {REPO}</code></p>
<p><button type="button" class="chip" data-copy="cite-database">Copy citation</button></p></div>
<p>Quotations from Tartt's writing and interviews are her words as printed by the original
publisher, reproduced for non-commercial research. Descriptive prose in the reference is the
compiler's characterisation, not hers — and quotations from her <em>fiction</em> are her
characters' words, not her opinions.</p>

<h2 id="rights">Rights</h2>
<p>The original research and compilation are licensed
<a class="ext" target="_blank" rel="noopener" href="{BLOB}LICENSE">CC BY-NC 4.0</a>. Third-party
source captures, cover images and quoted text remain under their owners' copyright. To request
removal of anything, open an issue on the
<a class="ext" target="_blank" rel="noopener" href="{REPO}/issues">repository</a>.</p>

<h2 id="build">How the site is built</h2>
<p>A dependency-light Python generator (<code>scripts/build_site.py</code> with
<code>scripts/sitelib/</code>) reads the database and writes static HTML into <code>docs/</code>.
There is no framework, no CDN, no webfont and no tracking: the stylesheet and a small progressive-
enhancement script are the only assets. Re-run <code>python3 scripts/build_site.py</code> after
editing the database to regenerate the site.</p>
<p>Images are served as downscaled derivatives. If one is missing, the page falls back to the
full-resolution original in the repository, so a plate is never simply broken — it just loads
more slowly until the derivatives are rebuilt.</p>
</div>""")
    site.page(path, title="About this site & how to cite it", body=body, nav=None,
              description="What the Donna Tartt research database is, what it leaves out, "
                          "and how to cite it.")


def build_404(site):
    p = P(site, "404.html")
    body = (f'<div class="hero"><p class="eyebrow">404</p><h1>Not catalogued</h1>'
            f'<p class="dek">That page is not part of this database. '
            f'Try the <a href="{e(p.u("editions/index.html"))}">editions</a>, the '
            f'<a href="{e(p.u("interviews/index.html"))}">interviews</a>, or the '
            f'<a href="{e(p.u("reference/index.html"))}">master reference</a>.</p>'
            f"{FLOURISH}</div>")
    site.page("404.html", title="Not found", body=body, nav=None)


def prune_images(pages_root):
    """Delete image derivatives no page references.

    `ImageSet` builds a display copy and a thumb for everything it is asked
    about, but a given image is often used at only one of the two sizes. The
    leftovers would otherwise be committed and go stale, so they are swept once
    the pages are written and the real set of references is known.
    """
    img_root = os.path.join(pages_root, "assets", "img")
    if not os.path.isdir(img_root):
        return 0, 0
    used = set()
    for dp, _, files in os.walk(pages_root):
        for fn in files:
            if not fn.endswith(".html"):
                continue
            page = os.path.join(dp, fn)
            with open(page, encoding="utf-8") as fh:
                for m in re.finditer(r'(?:src|href)="([^"]*assets/img/[^"]+)"', fh.read()):
                    used.add(os.path.normpath(os.path.join(dp, m.group(1))))
    removed = freed = 0
    for dp, _, files in os.walk(img_root, topdown=False):
        for fn in files:
            path = os.path.join(dp, fn)
            if path not in used:
                freed += os.path.getsize(path)
                os.remove(path)
                removed += 1
        if not os.listdir(dp):
            os.rmdir(dp)
    return removed, freed


def build_sitemap(site):
    today = time.strftime("%Y-%m-%d")
    urls = "".join(
        f"<url><loc>{SITE_URL}{path if path != 'index.html' else ''}</loc>"
        f"<lastmod>{today}</lastmod></url>\n" for path in sorted(set(site.pages)))
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n")


# ======================================================================= main
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--clean", action="store_true",
                    help="delete docs/ first (forces every image derivative to rebuild)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    if args.clean and os.path.isdir(OUT):
        shutil.rmtree(OUT)
    else:
        for dirpath, _, files in os.walk(OUT) if os.path.isdir(OUT) else ():
            for fn in files:
                if fn.endswith((".html", ".xml", ".txt", ".css", ".js")):
                    os.remove(os.path.join(dirpath, fn))

    os.makedirs(OUT, exist_ok=True)
    site = Site(verbose=args.verbose)
    c = site.corpus

    write(".nojekyll", "")
    write("assets/site.css", theme.CSS)
    write("assets/site.js", theme.JS.replace("__RAW_BASE__", RAW))

    build_home(site, c)
    build_editions(site, c)
    build_signed(site, c)
    build_essays(site, c)
    build_contributions(site, c)
    build_press(site, c)
    for it in c.items:
        item_page(site, it)
    build_about(site, c)
    build_interviews(site, c)
    build_reference(site, c)
    doc_page(site, "verification.html", C.VERIFY_NAME, nav=None, eyebrow="Apparatus",
             title="Verification report",
             dek="The fact-check layer behind the reference: documented corrections, the "
                 "verification method, and the claims that remain open.",
             sidebar_title="Contents")
    build_sources(site, c)
    build_colophon(site, c)
    build_404(site)
    build_sitemap(site)

    removed, freed = prune_images(OUT)
    print(f"pages: {len(site.pages)} written to docs/")
    print(site.img.report())
    print(f"pruned {removed} unused derivatives ({freed / 1e6:.1f} MB)")
    print(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()

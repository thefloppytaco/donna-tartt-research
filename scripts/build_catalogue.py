#!/usr/bin/env python3
"""
Build the browsable per-item catalogue for the Donna Tartt research repo.

Reads:  data/cover_manifest.csv, Donna_Tartt_Collectors_Reference.md,
        assets/sources/archive/excerpts/*, reference/interviews/originals/*.md
Writes: catalogue/<id>.md (one page per item) and CATALOGUE.md (gallery index)

The catalogue/ directory and CATALOGUE.md are pure build artifacts — re-run this
script after editing the manifest or sources. Idempotent (stable output).

Usage:  python3 scripts/build_catalogue.py          # generate
        python3 scripts/build_catalogue.py --check   # verify links/images resolve
"""
import csv, os, re, sys, glob, html as htmllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "data", "cover_manifest.csv")
REFERENCE = os.path.join(ROOT, "Donna_Tartt_Collectors_Reference.md")
REF_NAME = "Donna_Tartt_Collectors_Reference.md"
EXCERPT_DIR = os.path.join(ROOT, "assets", "sources", "archive", "excerpts")
EXCERPT_REL = "assets/sources/archive/excerpts"
FULLTEXT_DIR = os.path.join(ROOT, "assets", "sources", "fulltext")
FULLTEXT_REL = "assets/sources/fulltext"
SCAN_DIR = os.path.join(ROOT, "assets", "images", "scans")
INTERVIEW_DIR = os.path.join(ROOT, "reference", "interviews", "originals")
CAT_DIR = os.path.join(ROOT, "catalogue")

# id -> excerpt file we hold (verified to exist on disk)
EMBED = {
    "CON-016": "Tartt-OnBarrieAndStevenson-FTRv1-2005-pp66-71.md",
    "CON-019": "Tartt-Rimbaud-FourPoems-FTRv2-2006-pp128-135.md",
    "CON-020": "Tartt-Foreword-LifeStFrancis-2005-pp-v-ix.md",
    "CON-021": "Tartt-Hummingbird-WhenWeWereYoung-2004-pp294-297.md",
    "CON-018": "Tartt-EarlyTimesInMississippi-CornbreadNation5-2014-pp275-277.md",
    "CON-004": "Tartt-TrueCrime-MurderForLove-Penzler-1996-poem-p323.html",
    "CON-022": "Tartt-LegendaryAuthorsClothes-Newman-2017-ch31.md",
}
PDF_LINK = {
    "CON-007": "Tartt-ErinParish-IntoTheBlueAgain-Coploff-1997-catalog.pdf",
    "CON-008": "Tartt-PenMeetsPaint-Mauritshuis-2022-Goldfinch-essay.pdf",
    "CON-024": "Tartt-Livraison-No2-2006-AnonymousPartygoer-letter.pdf",
}
NOVEL_WORKS = {"TSH", "TLF", "TG"}
GROUP_ORDER = ["TSH", "TLF", "TG", "Short Fiction", "Nonfiction", "Contributions", "Press"]
GROUP_TITLE = {
    "TSH": "The Secret History (1992)", "TLF": "The Little Friend (2002)",
    "TG": "The Goldfinch (2013)", "Short Fiction": "Short Fiction",
    "Nonfiction": "Nonfiction & Essays", "Contributions": "Introductions & Contributions",
    "Press": "Press & Ephemera",
}
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def slug(text):
    """GitHub-accurate anchor: lowercase, keep [\\w- ], spaces->'-' (no collapsing)."""
    s = "".join(ch for ch in text.lower() if re.match(r"[\w\- ]", ch))
    return s.replace(" ", "-")


def build_anchor_map():
    """section token (e.g. '2.1','2.3a','8.5') -> github anchor of its heading."""
    seen, m = {}, {}
    for line in open(REFERENCE, encoding="utf-8"):
        hm = re.match(r"^(#{2,4})\s+(.*)$", line.rstrip("\n"))
        if not hm:
            continue
        text = hm.group(2).strip()
        a = slug(text)
        if a in seen:
            seen[a] += 1; a = f"{a}-{seen[a]}"
        else:
            seen[a] = 0
        tok = re.match(r"^([0-9]+[A-Za-z]?(?:\.[0-9A-Za-z]+)*)\b", text)
        if tok and tok.group(1) not in m:
            m[tok.group(1)] = a
    return m


def build_asset_index():
    """basename -> repo-relative path (prefer assets/images over deeper dirs)."""
    idx = {}
    for dp, _, files in os.walk(os.path.join(ROOT, "assets")):
        for fn in files:
            rel = os.path.relpath(os.path.join(dp, fn), ROOT)
            idx.setdefault(fn, rel)
    return idx


def resolve_cover(cover_image, assets):
    ci = (cover_image or "").strip()
    if not ci or not ci.lower().endswith(IMG_EXT):
        return None
    return assets.get(os.path.basename(ci))


SRC_EXT = (".pdf", ".html", ".txt", ".webarchive")


def build_source_index():
    """Index public source documents: basename->relpath and S-number->relpath."""
    by_base, by_snum = {}, {}
    for sub in ("assets/sources", "assets/articles"):
        for dp, _, files in os.walk(os.path.join(ROOT, sub)):
            if "_files" in dp:  # skip web-asset dependency dirs
                continue
            for fn in files:
                if not fn.lower().endswith(SRC_EXT):
                    continue
                rel = os.path.relpath(os.path.join(dp, fn), ROOT)
                by_base.setdefault(fn, rel)
                sm = re.match(r"S(\d+)_", fn)
                if sm:
                    by_snum.setdefault(int(sm.group(1)), rel)
    return by_base, by_snum


def parse_sections():
    """section token -> body text (between this heading and the next)."""
    ref = open(REFERENCE, encoding="utf-8").read()
    parts = re.split(r"(?m)^(#{2,4} .*)$", ref)
    out = {}
    for i in range(1, len(parts), 2):
        head, body = parts[i], parts[i + 1] if i + 1 < len(parts) else ""
        m = re.match(r"#{2,4} ([0-9]+[A-Za-z]?(?:\.[0-9A-Za-z]+)*)\b", head)
        if m:
            out[m.group(1)] = body
    return out


def prettify(basename):
    name = re.sub(r"\.(pdf|html|txt|webarchive)$", "", basename, flags=re.I)
    name = name.replace("_", " ").replace("-", " ").strip()
    return re.sub(r"\s+", " ", name)


def sources_for(section, sec_body, by_base, by_snum, exclude):
    """relpath -> basename for held source docs cited in this section's body."""
    body = sec_body.get(section, "")
    found = {}
    if body:
        for bn, rel in by_base.items():
            if bn in body:
                found[rel] = bn
        for sn in set(re.findall(r"\bS(\d+)\b", body)):
            rel = by_snum.get(int(sn))
            if rel:
                found[rel] = os.path.basename(rel)
        for p in re.findall(r"assets/(?:sources|articles)/[^\s)\"`\]]+", body):
            bn = os.path.basename(p.rstrip(".,);`"))
            if bn in by_base:
                found[by_base[bn]] = bn
    for rel in [r for r, bn in found.items() if bn in exclude]:
        del found[rel]
    return found


# sites that reproduce Tartt's actual full text (the "real thing"), surfaced even when
# they aren't on the Canonical-URL line
FULLTEXT_HOSTS = ("languageisavirus.com", "brickmag.com")


def original_links(section, sec_body):
    """Canonical/original-source URLs cited for this section (the 'real thing')."""
    body = sec_body.get(section, "")
    urls, lines = [], body.split("\n")
    for i, l in enumerate(lines):
        if "Canonical URL" in l:
            j = i
            while j < len(lines) and lines[j].strip():
                urls += re.findall(r'https?://[^\s)\]"<>]+', lines[j])
                j += 1
            break
    # also pull free-full-text host links from anywhere in the section
    for u in re.findall(r'https?://[^\s)\]"<>]+', body):
        if any(h in u for h in FULLTEXT_HOSTS):
            urls.append(u)
    out = []
    for u in urls:
        u = u.rstrip(".,);")
        if u not in out:
            out.append(u)
    return out


def url_label(u):
    m = re.match(r"https?://(?:www\.)?([^/]+)", u)
    return m.group(1) if m else u


def excerpt_body_md(path):
    """Strip the leading metadata block (up to & incl. first '---') from an excerpt .md."""
    txt = open(path, encoding="utf-8").read()
    parts = txt.split("\n---\n", 1)
    body = parts[1] if len(parts) == 2 else txt
    return body.strip()


def excerpt_body_html(path):
    """Crudely de-tag an .html excerpt into plain text (for the True Crime poem)."""
    raw = open(path, encoding="utf-8", errors="replace").read()
    raw = re.sub(r"(?is)<(script|style).*?</\1>", "", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?i)</p>", "\n\n", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = htmllib.unescape(raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()


def natkey(section):
    out = []
    for p in (section or "").split("."):
        mnum = re.match(r"(\d*)(.*)", p)
        out.append((int(mnum.group(1)) if mnum.group(1) else 0, mnum.group(2)))
    return out


def md_table(fields):
    rows = "\n".join(f"| {k} | {v} |" for k, v in fields if v not in (None, ""))
    return "| Field | Value |\n|---|---|\n" + rows


# ---------- page renderers ----------
def render_item(row, cover_rel, anchor, sources, origins):
    rid, work = row["id"], row["work"]
    name = row["edition_name"].strip() or rid
    out = [f"[← Back to the Catalogue](../CATALOGUE.md)", "", f"# {name}", ""]
    out.append(f"<sub>{GROUP_TITLE.get(work, work)} · item `{rid}`</sub>")
    out.append("")
    if cover_rel:
        out.append(f'<img src="../{cover_rel}" alt="{name}" width="280">')
    else:
        out.append("> **Cover missing** — no cover image is held for this item yet.")
    out.append("")
    out.append("### Reference details")
    out.append(md_table([
        ("Work", GROUP_TITLE.get(work, work)), ("Section", f"§{row['section']}" if row['section'] else ""),
        ("Edition", name), ("Country", row["country"]), ("Language", row["language"]),
        ("Publisher", row["publisher"]), ("Year", row["year"]),
        ("ISBN-13", row["isbn13"]), ("ISBN-10", row["isbn10"]), ("Status", row["status"]),
    ]))
    out.append("")
    if anchor:
        out.append(f"📖 **Full reference entry:** [§{row['section']} in the Collector's Reference](../{REF_NAME}#{anchor})")
        out.append("")
    if origins:
        links = " · ".join(f"[{url_label(u)}]({u})" for u in origins)
        out.append(f"🔗 **Read the original:** {links}")
        out.append("")
    if (row["status"] or "").startswith("not by Tartt"):
        out.append("> ⚠️ **Misattribution.** Research found no Donna Tartt content in this item. "
                   "It is listed here only to document — and correct — the false attribution.")
        out.append("")
    # full text
    out.append("### Full text")
    out.append("")
    hosted = os.path.join(FULLTEXT_DIR, f"{rid}.md")
    if os.path.exists(hosted):
        body = re.sub(r"^\s*<!--.*?-->\s*", "", open(hosted, encoding="utf-8").read(), flags=re.S)
        out.append(body.strip())
        out.append("")
        out.append("<sub>Full text reproduced for non-commercial research; original source linked "
                   "above. Hosted at <code>" + FULLTEXT_REL + f"/{rid}.md</code>.</sub>")
    elif glob.glob(os.path.join(SCAN_DIR, f"{rid}-p*.jpg")):
        out.append("_No machine-readable text available — the original is reproduced here as page scans:_")
        out.append("")
        for img in sorted(glob.glob(os.path.join(SCAN_DIR, f"{rid}-p*.jpg"))):
            out.append(f'<img src="../{os.path.relpath(img, ROOT)}" width="660" alt="scanned page">')
            out.append("")
    elif rid in EMBED:
        fn = EMBED[rid]; p = os.path.join(EXCERPT_DIR, fn)
        body = excerpt_body_html(p) if fn.endswith(".html") else excerpt_body_md(p)
        out.append(body)
        out.append("")
        out.append(f"<sub>Source: <code>{EXCERPT_REL}/{fn}</code> — regenerated by "
                   f"<code>scripts/build_catalogue.py</code>.</sub>")
    elif rid in PDF_LINK:
        fn = PDF_LINK[rid]
        out.append(f"The full text is held as a scanned PDF: "
                   f"[{fn}](../{EXCERPT_REL}/{fn}).")
    elif work in NOVEL_WORKS:
        out.append("_Full text not reproduced — this is one of Tartt's novels. See the reference "
                   "entry above for bibliographic detail._")
    elif work == "Short Fiction":
        out.append("_Full text not reproduced here. See the reference entry above and the original "
                   "publication for the complete story._")
    else:
        out.append("_No full text is held for this item. See the reference entry above and the "
                   "cited source._")
    out.append("")
    # sources & documents held for this item's section
    out.append("### Sources & documents held")
    out.append("")
    if sources:
        for rel in sorted(sources):
            bn = sources[rel]
            tag = " (Safari web-archive — download to view)" if bn.endswith(".webarchive") else \
                  " (PDF)" if bn.endswith(".pdf") else " (saved web page)" if bn.endswith(".html") else ""
            out.append(f"- [{prettify(bn)}](../{rel}){tag}")
        out.append("")
        out.append("<sub>Primary-source captures cited for this section of the reference. "
                   "PDFs and images open in GitHub's viewer; `.webarchive` files download.</sub>")
    else:
        out.append("_No primary-source scan is held for this item yet — see the reference entry "
                   "and the cited source above._")
    out.append("")
    out.append("---")
    out.append("[← Back to the Catalogue](../CATALOGUE.md)")
    return "\n".join(out) + "\n"


def render_interview(path):
    fn = os.path.basename(path)
    iid = "INT-" + os.path.splitext(fn)[0]
    txt = open(path, encoding="utf-8").read().strip()
    out = [f"[← Back to the Catalogue](../CATALOGUE.md)", "",
           "<sub>Interview · Donna Tartt in her own words</sub>", "",
           "> **Cover missing** — interviews are catalogued by transcript.", "",
           txt, "", "---", "[← Back to the Catalogue](../CATALOGUE.md)"]
    return iid, "\n".join(out) + "\n"


def interview_title(path):
    for line in open(path, encoding="utf-8"):
        if line.startswith("# "):
            t = line[2:].strip()
            return (t[:60] + "…") if len(t) > 61 else t
    return os.path.basename(path)


def cell(href, cover_rel, label, sub=""):
    if cover_rel:
        img = f'<img src="{cover_rel}" height="115" alt="{label}">'
    else:
        img = '<em>(cover<br>missing)</em>'
    s = f"<br><i>{sub}</i>" if sub else ""
    return (f'    <td align="center" width="150" valign="top">'
            f'<a href="{href}">{img}</a><br><sub><b>{label}</b>{s}</sub></td>')


def table(cells, cols=5):
    rows = []
    for i in range(0, len(cells), cols):
        rows.append("  <tr>\n" + "\n".join(cells[i:i + cols]) + "\n  </tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def short(name, n=40):
    name = name.strip()
    return (name[:n] + "…") if len(name) > n + 1 else name


def extra_title(fid):
    s = re.sub(r"^(INT-|P\d+_)", "", fid).replace("_", " — ")
    return s


def render_extra(fid):
    """Catalogue page for a hosted full text that has no manifest row (extra interview/byline)."""
    body = re.sub(r"^\s*<!--.*?-->\s*", "",
                  open(os.path.join(FULLTEXT_DIR, f"{fid}.md"), encoding="utf-8").read(), flags=re.S)
    out = ["[← Back to the Catalogue](../CATALOGUE.md)", "",
           "<sub>Interview / byline · Donna Tartt — full text</sub>", "",
           f"# {extra_title(fid)}", "",
           "> Catalogued by text (no cover).", "",
           body.strip(), "", "---", "[← Back to the Catalogue](../CATALOGUE.md)"]
    return "\n".join(out) + "\n"


# ---------- main ----------
def generate():
    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8")))
    anchors = build_anchor_map()
    assets = build_asset_index()
    by_base, by_snum = build_source_index()
    sec_body = parse_sections()
    # rebuild catalogue dir
    if os.path.isdir(CAT_DIR):
        for f in glob.glob(os.path.join(CAT_DIR, "*.md")):
            os.remove(f)
    os.makedirs(CAT_DIR, exist_ok=True)

    miss_cover = misattrib = with_src = workpages = 0
    for row in rows:
        cover = resolve_cover(row["cover_image"], assets)
        if not cover: miss_cover += 1
        if (row["status"] or "").startswith("not by Tartt"): misattrib += 1
        # Novels: cover image only (shown in the gallery) — no detail page.
        if row["work"] in NOVEL_WORKS:
            continue
        anchor = anchors.get(row["section"])
        exclude = {EMBED.get(row["id"]), PDF_LINK.get(row["id"])} - {None}
        sources = sources_for(row["section"], sec_body, by_base, by_snum, exclude)
        origins = original_links(row["section"], sec_body)
        if sources or row["id"] in EMBED or row["id"] in PDF_LINK: with_src += 1
        workpages += 1
        open(os.path.join(CAT_DIR, f"{row['id']}.md"), "w", encoding="utf-8").write(
            render_item(row, cover, anchor, sources, origins))

    interviews = []
    for p in sorted(glob.glob(os.path.join(INTERVIEW_DIR, "*.md"))):
        iid, page = render_interview(p)
        open(os.path.join(CAT_DIR, f"{iid}.md"), "w", encoding="utf-8").write(page)
        interviews.append((iid, interview_title(p)))

    # extra hosted full texts that have no manifest row (interviews / bylines)
    manifest_ids = {r["id"] for r in rows}
    extras = []
    for ft in sorted(glob.glob(os.path.join(FULLTEXT_DIR, "*.md"))):
        fid = os.path.splitext(os.path.basename(ft))[0]
        if fid in manifest_ids:
            continue
        open(os.path.join(CAT_DIR, f"{fid}.md"), "w", encoding="utf-8").write(render_extra(fid))
        extras.append((fid, extra_title(fid)))

    # ---- CATALOGUE.md ----
    total = len(rows) + len(interviews) + len(extras)
    fulltext_n = len(glob.glob(os.path.join(FULLTEXT_DIR, "*.md")))
    have = sum(1 for r in rows if resolve_cover(r["cover_image"], assets))
    novels = sum(1 for r in rows if r["work"] in NOVEL_WORKS)
    g = [f"# Donna Tartt — Complete Catalogue", "",
         f"**{total} items** · {len(rows)-novels} works + {len(interviews)+len(extras)} interviews & "
         f"bylines (full pages) · {novels} novel editions (cover gallery) · "
         f"**{fulltext_n} works with full text hosted here**.  ",
         "_Generated by `scripts/build_catalogue.py` — do not edit by hand._", "",
         "[← Back to the README](README.md)", "",
         "👆 **Works & interviews** open a full page — cover, reference info, a link to the original "
         "source, and the full text where we hold it. **Novel covers** open the full-size image; each "
         "novel's complete edition list lives in the reference.", ""]
    NOVEL_SEC = {"TSH": "2", "TLF": "3", "TG": "4"}
    by_work = {}
    for r in rows:
        by_work.setdefault(r["work"], []).append(r)
    for w in GROUP_ORDER:
        items = sorted(by_work.get(w, []), key=lambda r: natkey(r["section"]))
        if not items: continue
        if w in NOVEL_WORKS:
            na = anchors.get(NOVEL_SEC[w])
            hdr = f"## {GROUP_TITLE.get(w, w)} — {len(items)} editions"
            if na: hdr += f" · [full reference & edition list →]({REF_NAME}#{na})"
            g.append(hdr + "\n")
            cells = []
            for r in items:
                cov = resolve_cover(r["cover_image"], assets)
                href = cov if cov else (f"{REF_NAME}#{na}" if na else f"{REF_NAME}")
                cells.append(cell(href, cov, short(r["edition_name"] or r["id"]),
                                  "cover missing" if not cov else ""))
            g.append(table(cells)); g.append("")
        else:
            g.append(f"## {GROUP_TITLE.get(w, w)} ({len(items)})\n")
            cells = [cell(f"catalogue/{r['id']}.md", resolve_cover(r['cover_image'], assets),
                          short(r["edition_name"] or r["id"]),
                          "cover missing" if not resolve_cover(r['cover_image'], assets) else "")
                     for r in items]
            g.append(table(cells)); g.append("")
    # interviews group (transcripts + extra hosted interviews/bylines)
    g.append(f"## Interviews & bylines ({len(interviews) + len(extras)})\n")
    icells = [cell(f"catalogue/{iid}.md", None, short(title), "transcript")
              for iid, title in interviews]
    icells += [cell(f"catalogue/{fid}.md", None, short(title), "full text")
               for fid, title in extras]
    g.append(table(icells)); g.append("")
    open(os.path.join(ROOT, "CATALOGUE.md"), "w", encoding="utf-8").write("\n".join(g) + "\n")

    print(f"generated {workpages} work pages + {len(interviews)} interview pages + "
          f"{len(extras)} extra interview/byline pages ({novels} novel editions = cover gallery)")
    print(f"covers: {have} resolved / {miss_cover} missing | misattributions flagged: {misattrib}")
    print(f"full texts hosted in-repo: {fulltext_n} | work items with any held source: {with_src}/{workpages}")


def check():
    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8")))
    # detail pages are expected for non-novel works only (novels are cover-gallery only)
    ids = {r["id"] for r in rows if r["work"] not in NOVEL_WORKS}
    pages = {os.path.splitext(os.path.basename(p))[0]
             for p in glob.glob(os.path.join(CAT_DIR, "*.md"))}
    problems = []
    for i in ids - pages: problems.append(f"missing page for manifest id {i}")
    # valid anchors recomputed from reference
    valid_anchors = set()
    seen = {}
    for line in open(REFERENCE, encoding="utf-8"):
        hm = re.match(r"^#{2,4}\s+(.*)$", line.rstrip("\n"))
        if hm:
            a = slug(hm.group(1).strip())
            if a in seen: seen[a] += 1; a = f"{a}-{seen[a]}"
            else: seen[a] = 0
            valid_anchors.add(a)
    img_checked = link_checked = 0
    for p in glob.glob(os.path.join(CAT_DIR, "*.md")) + [os.path.join(ROOT, "CATALOGUE.md")]:
        base = os.path.dirname(p)
        txt = open(p, encoding="utf-8").read()
        for src in re.findall(r'<img src="([^"]+)"', txt):
            img_checked += 1
            if not os.path.exists(os.path.normpath(os.path.join(base, src))):
                problems.append(f"{os.path.relpath(p,ROOT)}: broken img {src}")
        for tgt in re.findall(r"\]\(([^)]+)\)", txt):
            t = tgt.split(" ")[0]
            path, _, frag = t.partition("#")
            if path.startswith(("http", "mailto")): continue
            link_checked += 1
            if path and not os.path.exists(os.path.normpath(os.path.join(base, path))):
                problems.append(f"{os.path.relpath(p,ROOT)}: broken link {t}")
            if frag and REF_NAME in path and frag not in valid_anchors:
                problems.append(f"{os.path.relpath(p,ROOT)}: anchor #{frag} not in reference")
    print(f"checked {len(pages)} pages, {img_checked} images, {link_checked} links")
    if problems:
        print(f"PROBLEMS ({len(problems)}):")
        for p in problems[:40]: print("  -", p)
        sys.exit(1)
    print("OK — all pages present, all images and links resolve.")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        generate()

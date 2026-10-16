"""
Loads the research database into plain Python objects for the site generator.

Nothing here invents content: every field traces to a file in the repository —
`data/cover_manifest.csv`, the master reference, the interview transcripts, the
contribution excerpts, and the primary-source captures under `assets/`.
The parsing conventions mirror `scripts/build_catalogue.py` so the website and
the Markdown catalogue describe the same corpus.
"""
import csv
import glob
import os
import re

from . import markdown as md

# ---------------------------------------------------------------- repo layout
REF_NAME = "Donna_Tartt_Collectors_Reference.md"
ABOUT_NAME = "About_Donna_Tartt_Items.md"
VERIFY_NAME = "reports/Verification_Report.md"
INT_INDEX_NAME = "reference/Interviews_Source_Index.md"
EXCERPT_REL = "assets/sources/archive/excerpts"
FULLTEXT_REL = "assets/sources/fulltext"
SCAN_REL = "assets/images/scans"
INTERVIEW_REL = "reference/interviews/originals"

# id -> the excerpt of Tartt's own writing we hold for it (from build_catalogue.py)
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

NOVELS = ("TSH", "TLF", "TG")
WORK_TITLE = {
    "TSH": "The Secret History",
    "TLF": "The Little Friend",
    "TG": "The Goldfinch",
    "Short Fiction": "Short Fiction",
    "Nonfiction": "Nonfiction & Essays",
    "Contributions": "Introductions & Contributions",
    "Press": "Press & Ephemera",
}
WORK_YEAR = {"TSH": "1992", "TLF": "2002", "TG": "2013"}
NOVEL_SECTION = {"TSH": "2", "TLF": "3", "TG": "4"}

# which part of the site each manifest `work` belongs to
SECTION_OF_WORK = {
    "TSH": "editions", "TLF": "editions", "TG": "editions",
    "Short Fiction": "essays", "Nonfiction": "essays",
    "Contributions": "contributions", "Press": "press",
}

SRC_EXT = (".pdf", ".html", ".txt", ".webarchive")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")

SOURCE_KIND = {
    ".pdf": "PDF", ".html": "saved web page",
    ".webarchive": "Safari web-archive", ".txt": "text capture",
}

# hosts that reproduce Tartt's own full text (mirrors build_catalogue.py)
FULLTEXT_HOSTS = ("languageisavirus.com", "brickmag.com")


# ============================================================ small utilities
def read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as fh:
        return fh.read()


def natkey(section):
    out = []
    for part in (section or "").split("."):
        m = re.match(r"(\d*)(.*)", part)
        out.append((int(m.group(1)) if m.group(1) else 0, m.group(2)))
    return out


def prettify(basename):
    name = re.sub(r"\.(pdf|html|txt|webarchive)$", "", basename, flags=re.I)
    name = re.sub(r"^S\d+_", "", name)
    name = name.replace("_", " ").replace("-", " ").strip()
    return re.sub(r"\s+", " ", name)


def host_of(url):
    m = re.match(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1) if m else url


# ================================================================== the corpus
class Corpus:
    def __init__(self, root):
        self.root = root
        self.reference = read(root, REF_NAME)
        self.rows = self._manifest()
        self.anchors = self._anchor_map()
        self.sec_body = self._sections()
        self.images = self._image_index()
        self.src_by_base, self.src_by_num = self._source_index()
        self.items = [Item(self, r) for r in self.rows]
        self.by_id = {it.id: it for it in self.items}
        self.interviews = [Interview(self, p) for p in sorted(
            glob.glob(os.path.join(root, INTERVIEW_REL, "*.md")))]
        self.extras = self._extra_fulltexts()
        self.tier_b = self._tier_b()

    # ----------------------------------------------------------------- loaders
    def _manifest(self):
        with open(os.path.join(self.root, "data", "cover_manifest.csv"),
                  encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def _anchor_map(self):
        """section token (e.g. '2.1', '7.21') -> document-wide GitHub anchor."""
        seen, out = {}, {}
        for text, _lvl in self.headings():
            a = md.github_slug(text)
            if a in seen:
                seen[a] += 1
                a = f"{a}-{seen[a]}"
            else:
                seen[a] = 0
            tok = re.match(r"^([0-9]+[A-Za-z]?(?:\.[0-9A-Za-z]+)*)\b", text)
            if tok and tok.group(1) not in out:
                out[tok.group(1)] = a
        return out

    def headings(self):
        for line in self.reference.split("\n"):
            m = re.match(r"^(#{2,4})\s+(.*)$", line.rstrip())
            if m:
                yield m.group(2).strip(), len(m.group(1))

    def _sections(self):
        """section token -> raw body between its heading and the next heading."""
        parts = re.split(r"(?m)^(#{2,4} .*)$", self.reference)
        out = {}
        for i in range(1, len(parts), 2):
            head = parts[i]
            body = parts[i + 1] if i + 1 < len(parts) else ""
            m = re.match(r"#{2,4} ([0-9]+[A-Za-z]?(?:\.[0-9A-Za-z]+)*)\b", head)
            if m and m.group(1) not in out:
                out[m.group(1)] = body
        return out

    def _image_index(self):
        """basename -> path relative to assets/images (first match wins)."""
        base = os.path.join(self.root, "assets", "images")
        idx = {}
        for dp, _, files in os.walk(base):
            for fn in sorted(files):
                if os.path.splitext(fn)[1].lower() in IMG_EXT:
                    idx.setdefault(fn, os.path.relpath(os.path.join(dp, fn), base)
                                   .replace(os.sep, "/"))
        return idx

    def _source_index(self):
        by_base, by_num = {}, {}
        for sub in ("assets/sources", "assets/articles"):
            for dp, _, files in os.walk(os.path.join(self.root, sub)):
                if "_files" in dp:
                    continue
                for fn in sorted(files):
                    if not fn.lower().endswith(SRC_EXT):
                        continue
                    rel = os.path.relpath(os.path.join(dp, fn), self.root).replace(os.sep, "/")
                    by_base.setdefault(fn, rel)
                    m = re.match(r"S(\d+)_", fn)
                    if m:
                        by_num.setdefault(int(m.group(1)), rel)
        return by_base, by_num

    def _extra_fulltexts(self):
        """Hosted full texts with no manifest row — extra interviews and bylines."""
        known = {r["id"] for r in self.rows}
        out = []
        for path in sorted(glob.glob(os.path.join(self.root, FULLTEXT_REL, "*.md"))):
            fid = os.path.splitext(os.path.basename(path))[0]
            if fid not in known:
                out.append(Extra(self, fid, path))
        return out

    def _tier_b(self):
        """The `B.n` entries of About_Donna_Tartt_Items.md, as structured blocks."""
        text = read(self.root, ABOUT_NAME)
        _, body = md.split_front_matter(text)
        blocks, cur = [], None
        for line in body.split("\n"):
            m = re.match(r"^##\s+(B\.\d+)\s+(.*)$", line)
            if m:
                cur = {"id": m.group(1), "title": m.group(2).strip(), "lines": []}
                blocks.append(cur)
            elif re.match(r"^##\s+", line):
                cur = None
            elif cur is not None:
                cur["lines"].append(line)
        for b in blocks:
            lines = b["lines"]
            while lines and (not lines[-1].strip() or re.match(r"^\s*-{3,}\s*$", lines[-1])):
                lines.pop()
            b["body"] = "\n".join(lines)
            m = re.search(r"\*\*Cover:\*\*\s*`([^`]+)`", b["body"])
            b["cover"] = None
            if m:
                rel = os.path.relpath(m.group(1), "assets/images").replace(os.sep, "/")
                if os.path.isfile(os.path.join(self.root, "assets", "images", rel)):
                    b["cover"] = rel
            b["body"] = re.sub(r"(?m)^\*\*Cover:\*\*.*\n?", "", b["body"]).strip()
        return blocks

    # ------------------------------------------------------------- lookups
    def source_kind(self, basename):
        return SOURCE_KIND.get(os.path.splitext(basename)[1].lower(), "")

    def sources_for_section(self, section, exclude=()):
        """{repo path: basename} of held captures cited in this reference section."""
        body = self.sec_body.get(section, "")
        if not body:
            return {}
        found = {}
        for bn, rel in self.src_by_base.items():
            if bn in body:
                found[rel] = bn
        for num in set(re.findall(r"\bS(\d+)\b", body)):
            rel = self.src_by_num.get(int(num))
            if rel:
                found[rel] = os.path.basename(rel)
        for path in re.findall(r"assets/(?:sources|articles)/[^\s)\"`\]]+", body):
            bn = os.path.basename(path.rstrip(".,);`"))
            if bn in self.src_by_base:
                found[self.src_by_base[bn]] = bn
        for rel in [r for r, bn in found.items() if bn in exclude]:
            del found[rel]
        return found

    def originals_for_section(self, section):
        """Canonical / free-full-text URLs cited for a reference section."""
        body = self.sec_body.get(section, "")
        urls, lines = [], body.split("\n")
        for i, line in enumerate(lines):
            if "Canonical URL" in line:
                j = i
                while j < len(lines) and lines[j].strip():
                    urls += re.findall(r'https?://[^\s)\]"<>]+', lines[j])
                    j += 1
                break
        for u in re.findall(r'https?://[^\s)\]"<>]+', body):
            if any(h in u for h in FULLTEXT_HOSTS):
                urls.append(u)
        out = []
        for u in urls:
            u = u.rstrip(".,);")
            if u not in out:
                out.append(u)
        return out

    # -------------------------------------------------------------- groupings
    def group(self, work):
        items = [it for it in self.items if it.work == work]
        return sorted(items, key=lambda it: natkey(it.section))

    def signed_items(self):
        """Items whose edition name marks them as signed / limited / inscribed."""
        pat = re.compile(r"\bsign|limited|lettered|numbered|inscrib|deluxe|indiespensable",
                         re.I)
        return [it for it in self.items
                if pat.search(it.name) and it.work in NOVELS or
                (pat.search(it.name) and it.work == "Contributions")]


# ===================================================================== records
class Item:
    """One row of `data/cover_manifest.csv`, with everything we hold for it."""

    def __init__(self, corpus, row):
        c = self.corpus = corpus
        self.row = row
        self.id = row["id"].strip()
        self.work = row["work"].strip()
        self.section = row["section"].strip()
        self.name = row["edition_name"].strip() or self.id
        self.country = row["country"].strip()
        self.language = row["language"].strip()
        self.publisher = row["publisher"].strip()
        self.year = row["year"].strip()
        self.isbn13 = row["isbn13"].strip()
        self.isbn10 = row["isbn10"].strip()
        self.status = row["status"].strip()
        self.work_title = WORK_TITLE.get(self.work, self.work)
        self.site_section = SECTION_OF_WORK.get(self.work, "press")
        self.is_novel = self.work in NOVELS
        self.misattributed = self.status.startswith("not by Tartt")

        ci = (row["cover_image"] or "").strip()
        self.cover = None
        if ci and ci.lower().endswith(IMG_EXT):
            self.cover = c.images.get(os.path.basename(ci))

        self.ref_anchor = c.anchors.get(self.section)
        self.excerpt = EMBED.get(self.id)
        self.pdf = PDF_LINK.get(self.id)
        self.scans = [os.path.relpath(p, os.path.join(c.root, "assets", "images"))
                      .replace(os.sep, "/")
                      for p in sorted(glob.glob(os.path.join(
                          c.root, SCAN_REL, f"{self.id}-p*.jpg")))]
        ft = os.path.join(c.root, FULLTEXT_REL, f"{self.id}.md")
        self.fulltext_path = ft if os.path.isfile(ft) else None
        exclude = {self.excerpt, self.pdf} - {None}
        self.sources = c.sources_for_section(self.section, exclude)
        self.originals = c.originals_for_section(self.section)

    @property
    def has_text(self):
        return bool(self.fulltext_path or self.excerpt or self.scans)

    @property
    def url(self):
        return f"{self.site_section}/{self.id}.html"

    def search_blob(self):
        bits = [self.id, self.name, self.work_title, self.publisher, self.country,
                self.language, self.year, self.isbn13, self.isbn10, self.status]
        return " ".join(b for b in bits if b)

    def body_html(self, rw):
        """The item's own full text, where the repository holds it."""
        c = self.corpus
        if self.fulltext_path:
            raw = re.sub(r"^\s*<!--.*?-->\s*", "",
                         open(self.fulltext_path, encoding="utf-8").read(), flags=re.S)
            return md.render(raw, rw, heading_level=3), f"{FULLTEXT_REL}/{self.id}.md"
        if self.excerpt:
            path = os.path.join(c.root, EXCERPT_REL, self.excerpt)
            if self.excerpt.endswith(".html"):
                text = _detag(open(path, encoding="utf-8", errors="replace").read())
                return f'<div class="verse">{md.inline(text, rw)}</div>', \
                       f"{EXCERPT_REL}/{self.excerpt}"
            raw = open(path, encoding="utf-8").read()
            parts = raw.split("\n---\n", 1)
            body = parts[1] if len(parts) == 2 else raw
            return md.render(body.strip(), rw, heading_level=3), \
                f"{EXCERPT_REL}/{self.excerpt}"
        return None, None

    def fulltext_source_url(self):
        """The URL a hosted full text was retrieved from, per its header comment."""
        if not self.fulltext_path:
            return None
        head = open(self.fulltext_path, encoding="utf-8").read(400)
        m = re.search(r"retrieved from (https?://\S+?)(?:\s|-->)", head)
        return m.group(1) if m else None


class Header:
    """The `**Key:** value` provenance block that tops transcripts and excerpts."""

    ORDER = ["Outlet", "Publication", "Source", "Date", "Interviewer",
             "Author/Interviewer", "Host/Interviewer", "Host", "Author", "Byline",
             "Reporter", "Type", "Language", "Length", "Header", "Signature",
             "Copyright", "Subhead", "Context", "Note", "Photo credit",
             "Original URL", "LIV reprint", "Source captured", "Source PDF",
             "Captured", "Extracted"]

    def __init__(self, text):
        self.title = ""
        self.fields = {}
        self.note = ""
        self.body = text
        head, sep, body = text.partition("\n---\n")
        if not sep:                     # no divider: treat the lead block as header
            head, body = text, ""
        lines = head.split("\n")
        notes = []
        for line in lines:
            m = re.match(r"^#\s+(.*)$", line)
            if m and not self.title:
                self.title = m.group(1).strip()
                continue
            m = re.match(r"^\*\*([^*:]+):\*\*\s*(.*)$", line.strip())
            if m:
                self.fields[m.group(1).strip()] = m.group(2).strip()
                continue
            if line.strip():
                notes.append(line.strip())
        self.note = " ".join(notes)
        self.body = body if sep else ""

    def ordered(self):
        keys = [k for k in self.ORDER if k in self.fields]
        keys += [k for k in self.fields if k not in self.ORDER]
        return [(k, self.fields[k]) for k in keys]

    def url(self):
        for key in ("Original URL", "LIV reprint", "Source captured"):
            v = self.fields.get(key, "")
            m = re.search(r"https?://\S+", v)
            if m:
                return m.group(0).rstrip(".,);")
        return None


class Interview:
    """One transcript under reference/interviews/originals/."""

    def __init__(self, corpus, path):
        self.corpus = corpus
        self.path = path
        self.repo_path = os.path.relpath(path, corpus.root).replace(os.sep, "/")
        self.basename = os.path.basename(path)
        self.stem = os.path.splitext(self.basename)[0]
        self.id = "INT-" + self.stem
        raw = open(path, encoding="utf-8").read()
        self.header = Header(raw)
        self.title = self.header.title or prettify(self.basename)
        self.date = self.header.fields.get("Date", "")
        self.outlet = self.header.fields.get("Outlet", "")
        self.interviewer = next(
            (self.header.fields[k] for k in
             ("Interviewer", "Author/Interviewer", "Host/Interviewer", "Host",
              "Author", "Byline", "Reporter")
             if k in self.header.fields), "")
        m = re.match(r"^(\d{4})", self.stem)
        self.year = m.group(1) if m else ""
        self.slug = md.slug(self.stem)

    @property
    def url(self):
        return f"interviews/{self.slug}.html"

    def search_blob(self):
        return " ".join(x for x in (self.title, self.outlet, self.interviewer,
                                    self.date, self.year,
                                    self.header.fields.get("Type", "")) if x)


class Extra:
    """A hosted full text with no manifest row — an extra interview or byline."""

    def __init__(self, corpus, fid, path):
        self.corpus = corpus
        self.id = fid
        self.path = path
        self.repo_path = f"{FULLTEXT_REL}/{fid}.md"
        raw = open(path, encoding="utf-8").read()
        m = re.match(r"\s*<!--(.*?)-->", raw, re.S)
        self.note = (m.group(1).strip() if m else "")
        self.source_url = None
        if m:
            u = re.search(r"https?://\S+", m.group(1))
            self.source_url = u.group(0).rstrip(".,);") if u else None
        self.body_md = re.sub(r"^\s*<!--.*?-->\s*", "", raw, flags=re.S).strip()
        first = next((l for l in self.body_md.split("\n") if l.strip()), "")
        self.title = re.sub(r"^#+\s*", "", first).strip() or fid
        if len(self.title) > 120:
            self.title = re.sub(r"^(INT-|P\d+_)", "", fid).replace("_", " — ")
        m = re.search(r"(\d{4})", fid)
        self.year = m.group(1) if m else ""
        self.slug = md.slug(fid)
        self.kind = "interview" if fid.startswith(("INT-", "P")) else "byline"

    @property
    def url(self):
        return f"interviews/{self.slug}.html"

    def search_blob(self):
        return f"{self.id} {self.title} {self.year}"


def _detag(raw):
    """Crude HTML -> text, for the one excerpt held as HTML (the True Crime poem)."""
    raw = re.sub(r"(?is)<(script|style).*?</\1>", "", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?i)</p>", "\n\n", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    import html as _h
    raw = _h.unescape(raw)
    return re.sub(r"\n{3,}", "\n\n", raw).strip()


# ======================================================== reference splitting
class RefSection:
    """One `## ` chapter of the master reference, as its own site page."""

    def __init__(self, token, title, lines, slug):
        self.token = token
        self.title = title
        self.lines = lines
        self.slug = slug

    @property
    def url(self):
        return f"reference/{self.slug}.html"

    @property
    def body_md(self):
        return "\n".join(self.lines)


def split_reference(text):
    """Split the master reference into chapters, skipping its Markdown TOC."""
    _, body = md.split_front_matter(text)
    chunks, cur = [], None
    for line in body.split("\n"):
        m = re.match(r"^##\s+(?!#)(.*)$", line)
        if m:
            title = m.group(1).strip()
            cur = {"title": title, "lines": []}
            chunks.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
    out = []
    gallery = None
    for ch in chunks:
        title = ch["title"]
        if title.lower().startswith("table of contents"):
            continue
        tok = re.match(r"^([0-9]+[A-Za-z]?|G\.\d+|Footnotes)\b", title)
        token = tok.group(1) if tok else md.slug(title)
        if title.startswith("G."):          # fold the visual index into one page
            if gallery is None:
                gallery = RefSection("G", "Visual cover index", [], "visual-cover-index")
                out.append(gallery)
            gallery.lines += [f"### {title}"] + ch["lines"]
            continue
        slug = md.slug(title)[:60].strip("-")
        out.append(RefSection(token, title, ch["lines"], slug))
    return out

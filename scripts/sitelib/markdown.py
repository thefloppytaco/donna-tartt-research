"""
A small, dependency-free Markdown renderer, tuned to the dialect actually used in
this repository (see ARCHITECTURE.md).

Deliberately a subset — it supports exactly what the corpus contains:

  * YAML front matter (stripped, returned separately)
  * ATX headings, thematic breaks, blockquotes
  * bullet and ordered lists, nested by *relative* indentation
  * pipe tables, including this repo's habit of emitting an empty header row and
    putting the real header in the first body row
  * inline: code spans, images, links, bold, italic, backslash escapes, bare URLs
  * bracketed footnote references (``[32]``) linked to the footnote list

Every URL passes through a caller-supplied ``link`` / ``image`` hook so the site
generator can rewrite repo-relative paths to site paths or GitHub blob URLs.
"""
import html
import re

__all__ = ["split_front_matter", "render", "Rewriter", "slug", "github_slug"]


# ---------------------------------------------------------------- front matter
def split_front_matter(text):
    """Return (front_matter_dict_ish, body). Only scalar `key: value` is parsed."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 3)
    if end == -1:
        return {}, text
    block, body = text[4:end], text[end + 5:]
    meta, key = {}, None
    for line in block.split("\n"):
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            meta[key] = m.group(2).strip().strip('"').rstrip("|").strip()
        elif key and line.strip():
            meta[key] = (meta[key] + " " + line.strip()).strip()
    return meta, body


# --------------------------------------------------------------------- anchors
def github_slug(text):
    """GitHub's heading-anchor algorithm (matches scripts/build_catalogue.py)."""
    s = "".join(ch for ch in text.lower() if re.match(r"[\w\- ]", ch))
    return s.replace(" ", "-")


def slug(text):
    """A friendlier slug for our own page/section ids."""
    s = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-") or "section"


# ------------------------------------------------------------------- rewriting
class Rewriter:
    """Hooks the renderer calls for every URL it meets.

    ``link(href)``     -> href for <a>
    ``image(src)``     -> (src, srcset_or_None, href_or_None[, extra_img_attrs])
    ``footnote(num)``  -> href for a bracketed footnote reference, or None
    """

    def link(self, href):
        return href

    def image(self, src):
        return src, None, None

    def footnote(self, num):
        return None


# ---------------------------------------------------------------------- inline
_CODE = re.compile(r"`([^`]+)`")
_IMG = re.compile(r"!\[([^\]]*)\]\(\s*([^\s)]+)(?:\s+\"((?:[^\"\\]|\\.)*)\")?\s*\)")
_LINK = re.compile(r"\[([^\]]+)\]\(\s*([^\s)]+)(?:\s+\"((?:[^\"\\]|\\.)*)\")?\s*\)")
_TRIPLE = re.compile(r"(?<!\*)\*{3}(?!\*)([^*\n]+?)(?<!\*)\*{3}(?!\*)")
_STARS = re.compile(r"\*{3,}")
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.S)
_ITAL = re.compile(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])", re.S)
_BARE = re.compile(r"(?<![\"'=>\w])(https?://[^\s<>\"')\]]+[^\s<>\"')\].,;:])")
_FNREF = re.compile(r"(?<![\w\[])\[(\d{1,3})\](?!\()")
_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!~&<>\"'$%^|])")

_PLACEHOLDER = "\x00{}\x00"


def _inline(text, rw, linkify_footnotes=False, _vault=None):
    """Render inline markup. HTML in the source is escaped, never passed through.

    Nested calls (a link label, an image caption) share the caller's vault and
    leave the placeholders in place: only the outermost call expands them, so
    the two levels can never claim the same placeholder index.
    """
    nested = _vault is not None
    vault = _vault if nested else []

    def stash(markup):
        vault.append(markup)
        return _PLACEHOLDER.format(len(vault) - 1)

    # 1. code spans first: nothing inside them is markup
    def code(m):
        return stash("<code>" + html.escape(m.group(1), quote=False) + "</code>")

    text = _CODE.sub(code, text)

    # 1b. asterisks that are not emphasis. The transcripts print censored words
    #     as runs of asterisks ("the ***** jumped"), which would otherwise be
    #     read as emphasis markers and mangle the sentence. A tight ***x***
    #     (three each side, nothing starred between) is still bold italic.
    def triple(m):
        return stash("<strong><em>" + _inline(m.group(1), rw, _vault=vault)
                     + "</em></strong>")

    text = _TRIPLE.sub(triple, text)
    text = _STARS.sub(lambda m: stash(m.group(0)), text)

    # 2. images (before links: ![..](..) also matches the link pattern)
    def image(m):
        alt, src, title = m.group(1), m.group(2), m.group(3) or ""
        alt = html.escape(_strip_markup(alt), quote=True)
        title = html.escape(_strip_markup(title.replace('\\"', '"')), quote=True)
        resolved, srcset, href, *rest = rw.image(src)
        if resolved is None:
            return stash("")
        attrs = f'src="{html.escape(resolved, quote=True)}" alt="{alt}" loading="lazy" decoding="async"'
        if srcset:
            attrs += f' srcset="{html.escape(srcset, quote=True)}"'
        if rest and rest[0]:
            attrs += " " + rest[0]
        img = f"<img {attrs}>"
        if href:
            img = f'<a class="plate-link" href="{html.escape(href, quote=True)}">{img}</a>'
        cap = (f"<figcaption>{_inline(title or alt, rw, _vault=vault)}</figcaption>"
               if (title or alt) else "")
        return stash(f'<figure class="plate">{img}{cap}</figure>')

    text = _IMG.sub(image, text)

    # 3. links
    def link(m):
        label, href = m.group(1), m.group(2)
        title = m.group(3) or ""
        resolved = rw.link(href)
        if resolved is None:
            return stash(_inline(label, rw, _vault=vault))
        t = f' title="{html.escape(_strip_markup(title), quote=True)}"' if title else ""
        ext = ' class="ext" target="_blank" rel="noopener"' if resolved.startswith("http") else ""
        return stash(f'<a href="{html.escape(resolved, quote=True)}"{ext}{t}>'
                     f"{_inline(label, rw, _vault=vault)}</a>")

    text = _LINK.sub(link, text)

    # 4. escape what's left, then emphasis
    text = html.escape(text, quote=False)
    text = _BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", text)
    text = _ITAL.sub(lambda m: f"<em>{m.group(1)}</em>", text)

    # 5. bare URLs
    def bare(m):
        u = m.group(1)
        return f'<a class="ext" target="_blank" rel="noopener" href="{u}">{_shorten_url(u)}</a>'

    text = _BARE.sub(bare, text)

    # 6. footnote references
    if linkify_footnotes:
        def fn(m):
            href = rw.footnote(m.group(1))
            if not href:
                return m.group(0)
            return (f'<a class="fnref" href="{html.escape(href, quote=True)}" '
                    f'title="Footnote {m.group(1)}">[{m.group(1)}]</a>')

        text = _FNREF.sub(fn, text)

    # 7. backslash escapes
    text = _ESCAPE.sub(lambda m: html.escape(m.group(1), quote=False), text)

    # 8. unstash — nested calls defer to the outermost one
    if nested:
        return text

    def pop(m):
        return vault[int(m.group(1))]

    for _ in range(8):
        if "\x00" not in text:
            break
        text = re.sub(r"\x00(\d+)\x00", pop, text)
    return text


def _strip_markup(text):
    text = _CODE.sub(r"\1", text)
    text = _LINK.sub(r"\1", text)
    text = _BOLD.sub(r"\1", text)
    text = _ITAL.sub(r"\1", text)
    return _ESCAPE.sub(r"\1", text)


def _shorten_url(u):
    show = re.sub(r"^https?://(www\.)?", "", u).rstrip("/")
    return html.escape(show if len(show) <= 58 else show[:55] + "…", quote=False)


# ----------------------------------------------------------------------- block
_H = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
_HR = re.compile(r"^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")
_UL = re.compile(r"^(\s*)([-*+])\s+(.*)$")
_OL = re.compile(r"^(\s*)(\d{1,3})[.)]\s+(.*)$")
_ROW = re.compile(r"^\s*\|(.*)\|\s*$")
_DIV = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


class _Renderer:
    def __init__(self, rw, heading_level=2, heading_sink=None, linkify_footnotes=False,
                 footnote_ids=False, anchor_fn=None):
        self.rw = rw
        self.base = heading_level
        self.sink = heading_sink          # called with (level, text, anchor)
        self.fn_links = linkify_footnotes
        self.fn_ids = footnote_ids        # give ordered-list items id="fn-N"
        self.anchor_fn = anchor_fn        # override id generation (doc-wide anchors)
        self.seen = {}

    def anchor(self, text):
        if self.anchor_fn:
            return self.anchor_fn(text)
        a = github_slug(text)
        n = self.seen.get(a)
        self.seen[a] = 0 if n is None else n + 1
        return a if n is None else f"{a}-{self.seen[a]}"

    def inline(self, text):
        return _inline(text, self.rw, self.fn_links)

    # -- driver
    def run(self, lines):
        out, i, n = [], 0, len(lines)
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            if _HR.match(line):
                out.append('<hr class="rule">')
                i += 1
                continue
            m = _H.match(line)
            if m:
                i += 1
                lvl = min(6, max(1, len(m.group(1)) + self.base - 2))
                text = m.group(2).strip()
                a = self.anchor(text)
                if self.sink:
                    self.sink(len(m.group(1)), text, a)
                out.append(f'<h{lvl} id="{a}">{self.inline(text)}'
                           f'<a class="anchor" href="#{a}" aria-label="Permalink">#</a></h{lvl}>')
                continue
            if line.lstrip().startswith(">"):
                i, block = self._gather(lines, i, lambda l: l.lstrip().startswith(">") or l.strip())
                inner = [re.sub(r"^\s*>\s?", "", l) for l in block]
                out.append("<blockquote>" + _Renderer(
                    self.rw, self.base, None, self.fn_links).run(inner) + "</blockquote>")
                continue
            if _ROW.match(line):
                i, tbl = self._table(lines, i)
                out.append(tbl)
                continue
            if _UL.match(line) or _OL.match(line):
                i, lst = self._list(lines, i)
                out.append(lst)
                continue
            i, para = self._para(lines, i)
            out.append(para)
        return "\n".join(out)

    @staticmethod
    def _gather(lines, i, keep):
        block = []
        while i < len(lines) and lines[i].strip() and keep(lines[i]):
            block.append(lines[i])
            i += 1
        return i, block

    # -- paragraph (with run-in heading detection)
    def _para(self, lines, i):
        buf = []
        while i < len(lines) and lines[i].strip() and not (
                _HR.match(lines[i]) or _H.match(lines[i]) or _ROW.match(lines[i])
                or _UL.match(lines[i]) or _OL.match(lines[i])
                or lines[i].lstrip().startswith(">")):
            buf.append(lines[i].strip())
            i += 1
        text = " ".join(buf)
        # a short, unpunctuated single line that introduces a list reads as a label
        nxt = next((l for l in lines[i:i + 2] if l.strip()), "")
        if (len(buf) == 1 and len(text) < 76 and not text.endswith((".", ":", "?", "!", ",", ";"))
                and (_UL.match(nxt) or _OL.match(nxt) or _ROW.match(nxt))):
            return i, f'<p class="runin">{self.inline(text)}</p>'
        return i, f"<p>{self.inline(text)}</p>"

    # -- lists
    def _list(self, lines, i):
        items, n = [], len(lines)
        while i < n:
            line = lines[i]
            if not line.strip():
                # a blank line only ends the list if what follows is not another item
                nxt = next((l for l in lines[i + 1:i + 3] if l.strip()), "")
                if _UL.match(nxt) or _OL.match(nxt):
                    i += 1
                    continue
                break
            m = _UL.match(line) or _OL.match(line)
            if not m:
                if items and line.startswith((" " * 4, "\t")):   # lazy continuation
                    items[-1][2] += " " + line.strip()
                    i += 1
                    continue
                break
            ordered = bool(_OL.match(line))
            num = int(m.group(2)) if ordered else None
            items.append([len(m.group(1)), ordered, m.group(3).strip(), num])
            i += 1
        if not items:
            return i + 1, ""
        floor = min(it[0] for it in items)
        for it in items:
            it[0] = (it[0] - floor) // 2
        return i, self._nest(items, 0)

    def _nest(self, items, depth):
        tag = "ol" if items and items[0][1] else "ul"
        start = items[0][3] if tag == "ol" and items[0][3] not in (None, 1) else None
        html_out = [f'<{tag} start="{start}">' if start else f"<{tag}>"]
        k = 0
        while k < len(items):
            indent, ordered, text, num = items[k]
            kid = k + 1
            while kid < len(items) and items[kid][0] > indent:
                kid += 1
            attr = f' id="fn-{num}"' if (self.fn_ids and depth == 0 and ordered and num) else ""
            inner = self.inline(text)
            if self.fn_ids and depth == 0 and ordered and num:
                inner = f'<span class="fnum">{num}.</span> {inner}'
            body = f"<li{attr}>{inner}"
            if kid > k + 1:
                body += self._nest(items[k + 1:kid], depth + 1)
            html_out.append(body + "</li>")
            k = kid
        html_out.append(f"</{tag}>")
        return "".join(html_out)

    # -- tables
    def _table(self, lines, i):
        rows, n = [], len(lines)
        while i < n and _ROW.match(lines[i]):
            if _DIV.match(lines[i]):
                rows.append(None)
            else:
                cells = _ROW.match(lines[i]).group(1).split("|")
                rows.append([c.strip() for c in cells])
            i += 1
        body = [r for r in rows if r is not None]
        if not body:
            return i, ""
        head, body = body[0], body[1:]
        # this repo often emits a blank header row and bolds the real header below
        if all(not c for c in head) and body:
            head, body = body[0], body[1:]
        width = max([len(head)] + [len(r) for r in body] or [0])

        def row(cells, tag):
            cells = list(cells) + [""] * (width - len(cells))
            return "<tr>" + "".join(
                f"<{tag}>{self.inline(c)}</{tag}>" for c in cells) + "</tr>"

        blank_head = all(not c for c in head)
        out = ['<div class="table-wrap"><table>']
        if not blank_head:
            out.append("<thead>" + row(head, "th") + "</thead>")
        elif head:
            body.insert(0, head)
        out.append("<tbody>" + "".join(row(r, "td") for r in body) + "</tbody>")
        out.append("</table></div>")
        return i, "".join(out)


def render(text, rw=None, heading_level=2, heading_sink=None,
           linkify_footnotes=False, footnote_ids=False, anchor_fn=None):
    """Render Markdown `text` to an HTML fragment."""
    rw = rw or Rewriter()
    text = text.replace("\r\n", "\n").replace(" ", " ")
    r = _Renderer(rw, heading_level, heading_sink, linkify_footnotes, footnote_ids, anchor_fn)
    return r.run(text.split("\n"))


def inline(text, rw=None):
    """Render only inline markup (for titles, labels, table cells)."""
    return _inline(text, rw or Rewriter())


def plain(text):
    """Strip markup entirely — for <title>, alt text and meta descriptions."""
    return _strip_markup(text)

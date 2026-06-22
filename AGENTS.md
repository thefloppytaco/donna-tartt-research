# AGENTS.md — How to research Donna Tartt with this database

You are an AI assistant pointed at a **Donna Tartt research database**. This file tells you how to
answer questions about Donna Tartt accurately and **with citations**, using the material in this
repository as your primary source. Read this file first, then work from the repo — not from memory.

## Prime directive

**Answer from the documents in this repo, and cite where each fact came from.** Donna Tartt is a
famously private author about whom a lot of misinformation circulates. Prefer what is written and
sourced here over your training data. If this repo doesn't support a claim, say so rather than
guessing — and never invent a quote.

When a user asks something like *"What does Donna Tartt think about X?"* or *"Has she ever said
anything about Y?"*, your job is to **search this corpus, read the matches, and reply with her
actual words (or the documented fact) plus a citation** the user can verify.

---

## Where the answers live

The searchable, high-value **text** corpus (search these first — they are Markdown/plain text):

| If the question is about… | Search here first |
|---|---|
| **Her opinions, views, what she "said about" something** | `reference/interviews/originals/` (15 transcripts, her direct quotes) and `assets/sources/archive/excerpts/` (her own essays/contributions) |
| **Her essays / nonfiction / contributed writing** | `assets/sources/archive/excerpts/`, then §6–§7 of the master reference |
| **A specific book, edition, printing, ISBN, signed copy** | `Donna_Tartt_Collectors_Reference.md` (the master reference) |
| **Authentication / signatures / forgery / value** | §9–§10 of the master reference |
| **Which interviews exist & whether they're captured** | `reference/Interviews_Source_Index.md` |
| **Items / press *about* her (not by her)** | `About_Donna_Tartt_Items.md` |
| **An edition's cover image / acquisition status** | `data/cover_manifest.csv` |
| **How a claim was verified** | `reports/Verification_Report.md` |

The **evidence** (not usually full-text-searchable, but cited *by* the text above): PDFs, HTML,
`.webarchive`, and images under `assets/`. Use these to (a) confirm a claim and (b) give the user a
concrete artifact to open. Full books Tartt contributed to live in `assets/sources/archive/` as
PDF/EPUB but live in a separate **private archive**; their relevant passages are already extracted
into `assets/sources/archive/excerpts/`, which is what's public here. Cite the excerpt + the original
publication, not the full book.

> **The `excerpts/` folder is mixed-format — don't only grep `*.md`.** It has 10 files: 6 Markdown
> and 1 HTML (`Tartt-TrueCrime-MurderForLove-...poem-p323.html` — her poem; greppable as text), plus
> 3 PDFs (her *Goldfinch* essay `Tartt-PenMeetsPaint-Mauritshuis-2022...pdf`, the *Livraison*
> letter, and the Erin Parish catalog text) that need a PDF reader. List the whole directory and
> open every file, not just the `.md` ones — otherwise you'll miss ~40% of her actual writing held here.

> For a structured map of every interview (with provenance and capture status), start from
> `reference/Interviews_Source_Index.md` — useful if you can't shell out to `grep`.

> The text corpus above is the whole story for answering questions — everything authoritative is in
> the Markdown files and the manifest.

---

## How to answer a question (recipe)

1. **Pull keywords** from the question (author names, book titles, themes — e.g. *Dickens*,
   *plot*, *Catholicism*, *editing*, *bourbon*, *Mississippi*).
2. **Search the text corpus** for those keywords. From the repo root, e.g.:
   ```bash
   # her own words — interviews + her essays
   grep -rin "dickens" reference/interviews/originals/ assets/sources/archive/excerpts/
   # widen to the whole reference + Tier B
   grep -rin "dickens" Donna_Tartt_Collectors_Reference.md About_Donna_Tartt_Items.md
   ```
   (No shell? Use whatever file-reading/search tools you have — the point is to scan these paths.)
3. **Open the matching files and read around the hits** for full context — don't quote a fragment
   out of context.
4. **Distinguish her voice from others'.** A quote inside an interview transcript or an excerpt of
   her writing is *her*. A line in the reference doc or a profile is the *compiler's / journalist's*
   characterization. Attribute accordingly.
5. **Answer with a citation.** Quote her exact words where possible, then point to the source.

## How to cite

Cite the **repo file** and, where the file records it, the **original publication** it came from.
Interview transcripts and excerpts carry full provenance in their headers (outlet, interviewer,
date, page numbers, original URL). Examples of good citations:

- > "…" — Donna Tartt, *Salon* interview with Laura Miller, 2013-10-22
  > (`reference/interviews/originals/2013-10-22_Salon_Laura-Miller_The-Fun-Thing-About-Writing.md`)
- > "…" — Donna Tartt, "Early Times in Mississippi," *Garden & Gun* 2007, repr. *Cornbread Nation 5*
  > (`assets/sources/archive/excerpts/Tartt-EarlyTimesInMississippi-CornbreadNation5-2014-pp275-277.md`)
- The US first edition had a $450,000 advance (Fein, *NYT*, 1992-11-16) — see
  `Donna_Tartt_Collectors_Reference.md` §2.1 and footnote citations.

**Path/reference conventions in this repo:** backtick paths like `` `assets/sources/...` `` are
written relative to the **repository root**. Source captures are numbered `S###` (45 files; the IDs
are sparse, running up to `S092` with gaps — `assets/sources/archive/S###_*.html`); the master
reference's claims map to those plus its 108 numbered footnotes.

---

## Worked examples

**Q: "What has Donna Tartt said about writing slowly / taking ten years per book?"**
→ `grep -rin "ten years\|slow\|years" reference/interviews/originals/` → read the hits (the
Telegraph 2002, USA Today 2002, Salon 2013 transcripts discuss her pace) → quote her directly with
the transcript citation.

**Q: "Does she have any connection to Dickens or 19th-century novels?"**
→ search interviews + excerpts + the essays sections → she discusses this in interviews and in her
critical writing; quote and cite.

**Q: "List every foreign-language first edition of *The Goldfinch*."**
→ this is bibliographic, not opinion: read §4 of `Donna_Tartt_Collectors_Reference.md` and/or filter
`data/cover_manifest.csv` for `TG-` foreign rows → present the table with cover status.

**Q: "Is this signed copy I'm looking at likely genuine?"**
→ §9 of the master reference: walk the user through the ink-color-by-program table (§9.2),
signature characteristics, and forgery red flags; cite the section.

---

## Guardrails

- **No fabricated quotes.** If you can't find it here, say "I don't find that in this archive."
- **Don't confuse Tartt with her characters or narrators.** Quotes from her *fiction* are not her
  personal opinions.
- **Flag uncertainty.** Some entries are single-sourced or marked open in
  `reports/Verification_Report.md` — say so when relevant.
- **Dates & editions are precise here** — prefer the repo's specifics (printings, states, ISBNs)
  over rounded-off general knowledge.
- **Respect the user's question scope.** Tier A = by Tartt; Tier B = about Tartt. Keep them straight.

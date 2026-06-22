# Donna Tartt Research Database — Architecture

A map of what lives in this repository and what each piece is for. For a friendlier orientation see
[`README.md`](README.md); to use this database with an AI assistant see [`AGENTS.md`](AGENTS.md).

## What the project is

A sourced public reference documenting every published edition, signed copy, contribution, and
notable artifact connected to American novelist Donna Tartt. The core deliverable is a long-form
Markdown reference (`Donna_Tartt_Collectors_Reference.md`) supported by a cover manifest,
primary-source captures, interview transcripts, and a verification report.

Two-tiered by design:
- **Tier A** — works authored or directly spoken by Tartt. Catalogued in the main reference.
- **Tier B** — items *featuring* Tartt as subject but not authored by her. Catalogued in
  `About_Donna_Tartt_Items.md`.

This is the **curated public edition**. Only one category is held privately — **full-book scans of
the works Tartt contributed to** (her specific contribution is excerpted into the public repo; the
complete copyrighted books are not redistributed). They live in a **separate
private archive** ([`donna-tartt-archive-private`](https://github.com/thefloppytaco/donna-tartt-archive-private)),
which is a path-identical overlay of `assets/` and is cited here by publication / URL. The public
repo carries the short extracted excerpts of Tartt's actual contributions, not the full books.

## Top-level layout

```
donna-tartt-research/
├── README.md                              ← navigation hub
├── AGENTS.md                              ← how to point an AI at this database
├── ARCHITECTURE.md                        ← this file
├── LICENSE                                ← usage & rights notice
├── Donna_Tartt_Collectors_Reference.md    ← master reference (Tier A: by Tartt)
├── About_Donna_Tartt_Items.md             ← Tier B: about Tartt
├── reference/   ← interview transcripts + interview index
├── reports/     ← verification & corrections
├── data/        ← cover manifest (CSV)
├── scripts/     ← ISBN validator + Wayback recovery scripts
└── assets/      ← cover images + primary-source captures (the evidence)
```

The two master reference documents stay at the repository **root** because their hundreds of inline
`assets/…` image and source links resolve relative to root.

## Reading documents (repository root)

- **`Donna_Tartt_Collectors_Reference.md`** — The master reference. ~4,900 lines covering every
  edition of *The Secret History* (1992), *The Little Friend* (2002), and *The Goldfinch* (2013):
  US/UK/foreign-language firsts, proofs and ARCs, signed limited editions, audiobooks, large-print
  and e-book editions; short fiction; nonfiction and essays; introductions, contributions, and
  audiobook narrations; press and ephemera; authentication tooling (signature characteristics,
  ink-color-by-program table, forgery red flags); auction history and association copies; translator
  cross-reference; translation-rights timeline; awards; numbered footnotes; and a visual cover index
  (§G). Each entry references its cover image in `assets/images/`.
- **`About_Donna_Tartt_Items.md`** — Tier B companion: items *about* Tartt (magazine profiles,
  signed posters, cover-blurb mentions). Cover images live in `assets/images/about/`.

## `reference/` — Tartt's own voice

- **`reference/Interviews_Source_Index.md`** — Index of every known Tartt interview (print/online,
  TV, radio/podcast, public events) plus her own bylines, pointing to the captured transcripts.
- **`reference/interviews/originals/`** — 15 Markdown transcripts of interviews captured to disk.
  Filename convention: `YYYY-MM-DD_Outlet_Interviewer_short-title.md`. **The best source for Tartt's
  direct quotes and opinions** — see [`AGENTS.md`](AGENTS.md).

## `reports/`

- **`reports/Verification_Report.md`** — A fact-check audit: documented factual corrections,
  verification methodology, and a source-confidence approach. The "show your work" layer behind the
  reference.

## `data/`

- **`data/cover_manifest.csv`** — Maps every edition (IDs like `TSH-001`, `TG-F12`, `MAG-008`) to its
  cover-image filename and acquisition status. Columns: `id, work, section, edition_name, country,
  language, publisher, year, isbn13, isbn10, cover_image, status`. Status values: `have`, `missing`,
  `alias (shares cover)`, `n/a`, `not by Tartt`.

## `scripts/`

- **`scripts/isbn_check.py`** — Validates ISBN-10 and ISBN-13 check digits (single + `--batch`).
- **`scripts/wayback_hunt.sh` / `wayback_hunt_retry.sh`** — Wayback-Machine CDX recovery sweeps that
  populate `assets/sources/archive/wayback/`.

## `assets/` — images and primary-source captures

### `assets/images/`
The cover-image pool referenced by the reference. Naming convention
`<TITLE>-<MARKET>-<PUBSHORT><YY>-cover_<source>.<ext>` (e.g. `TSH-US-KNOPF92-cover_wikipedia.jpg`).
Some early-build artifacts (`rId##.jpg`) remain where the reference embeds them.
- **`assets/images/about/`** — Tier B (about-Tartt) cover images.
- **`assets/images/magazines/`** — magazine and periodical covers where Tartt's work appeared or she
  was featured (Artforum, Esquire, GQ, Harper's, The New Yorker, Oxford American, Vanity Fair, etc.).
- **`assets/images/_retrieved/`** — foreign-edition covers (`TSH-F##`, `TLF-F##`, `TG-F##`) and
  contribution covers (`CON-###`) referenced by the foreign-firsts tables.

### `assets/sources/`
Saved primary-source captures — the project's hedge against link rot.
- **`archive/`** — Numbered dealer/press HTML captures (`S###_*.html`, IDs sparse up to S092) for
  points-of-issue references, ABAA dealer listings, foreign publishers, and library catalogs.
  - **`archive/excerpts/`** — Markdown (and a few PDF) extracts of Tartt's specific contributions
    (e.g. "Early Times in Mississippi," the St Francis foreword, the Rimbaud translation, the
    "True Crime" poem). **The full underlying books are in the private archive.**
  - **`archive/wayback/`** — Wayback-Machine snapshots harvested by the `scripts/` sweeps.
  - **`archive/manifest.json`** — Per-capture metadata.
- **`press_primary/`** — Highest-tier primary press PDFs (NYT, Vanity Fair, The Bookseller, Borzoi
  Reader, BNE record, etc.).
- **`auction_records/`** — Heritage Auctions lot PDFs for TSH and TLF.
- **`editions_foreign/`** — foreign-publisher and library catalog page captures (NDL Japan,
  Fusōsha, Marco Polo / Cite Taiwan) as HTML + `.webarchive` bundles.
- **`ebay/`** — `.webarchive` captures of notable eBay listings (Goldfinch UK signed/limited).
- **`misc_web_saves/`** — auction-aggregator and dealer listing saves (Barnebys, Sotheby's, etc.).
- **`sources_index.json`** — Index of files under `assets/sources/`.

> `.webarchive` files are Safari page bundles; they don't render on GitHub's web view but are kept
> as downloadable link-rot insurance.

### Not in the public repo (held in the private archive)
Only **full-book PDFs/EPUBs of the works Tartt contributed to** (e.g. *Cornbread Nation 5*,
*Maxwell: A Literary Portrait*, *Fairy Tale Review*, *True Grit*, *Life of St. Francis*). Her
specific contributions are excerpted into `assets/sources/archive/excerpts/`, and the books are
cited by publication / ISBN. See the private archive's `SOURCE_MAP.md` for the file-by-file mapping.

## File-type conventions

- **`.md`** — reference documents, reports, interview transcripts, contribution excerpts.
- **`.csv`** — the cover manifest.
- **`.json`** — machine-readable source/cover indexes.
- **`.html`** — saved web-page snapshots used as primary sources.
- **`.pdf`** — press articles, dealer/auction records, a few contribution scans.
- **`.jpg` / `.png` / `.gif` / `.webp`** — cover images, magazine covers, ephemera.
- **`.py` / `.sh`** — the ISBN validator and Wayback recovery scripts.

## How the pieces relate

```
                  Donna_Tartt_Collectors_Reference.md   ← single source of truth (Tier A)
                                   │
          ┌────────────────────────┼─────────────────────────────┐
   data/cover_manifest.csv   assets/images/*          assets/sources/* (HTML, PDF)
   (edition → image)         (cover images)           (primary-source captures)
          └──────────────── referenced inline in each entry ──────┘

   About_Donna_Tartt_Items.md (Tier B)  ──► assets/images/about/
   reference/Interviews_Source_Index.md ──► reference/interviews/originals/*.md
   reports/Verification_Report.md        ──► audit & corrections of the reference
   scripts/wayback_hunt.sh               ──► assets/sources/archive/wayback/

   private archive (full contributed-to books only) ──► overlay of assets/; cited by publication
```

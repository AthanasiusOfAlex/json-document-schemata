# Academic Book Schema

This document defines the JSON schema for a transcribed **academic book** — a monograph or an edited volume. It is the companion to the [journal-article](../journal-article/README.md) schema and shares its page-level model.

See [v1/schema.json](v1/schema.json) for the machine-readable JSON Schema, and [v1/examples/](v1/examples) for worked examples.

## Design in one paragraph

PDFTranscriber output is always **page-primary**: a transcription is an ordered array of physical pages, each carrying body `elements` and `footnotes`. A book uses that exact same page spine — the page, paragraph, heading, block-quote, and footnote definitions are shared with the journal-article schema in [`transcription-core.json`](../shared/transcription-core.json). On top of the page spine a book adds just two things:

1. **`publication`** — the publishing facts (publisher, ISBN, copyright, series).
2. **`structure`** — a logical outline of *divisions* (front matter, parts, chapters, sections, back matter) that **references into** the pages by `id`. The outline carries structural identity and location, never prose.

Because the outline only points at the pages, **any division can be sliced out together with the page range it spans, and what you get back has the same shape as a journal article.** That is how a chapter (or a Part) is used as a "quasi-article".

---

## Top-Level Structure

```json
{
  "metadata":    { ... },   // the transcription run (shared, optional)
  "frontMatter": { ... },   // the book's own title / authors / editors (shared, optional)
  "publication": { ... },   // the publishing facts (optional)
  "pages":       [ ... ],   // the physical, citable spine (required)
  "structure":   [ ... ]    // the logical division outline (optional overlay)
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `metadata` | `documentMetadata` | no | The transcription run. Shared definition. |
| `frontMatter` | `frontMatter` | no | The book's own title, authors, and (for edited volumes) editors. Shared definition. |
| `publication` | `publication` | no | The publishing facts. |
| `pages` | `[page]` | yes | The physical pages in document order — the citable spine. Shared definition. |
| `structure` | `[division]` | no | The logical outline; an overlay on `pages`. |

`metadata`, `frontMatter`, `page`, and `person` are defined in [`transcription-core.json`](../shared/transcription-core.json) and behave exactly as in the [journal-article schema](../journal-article/README.md) — including inline `[^fn-NNNN]` footnote references, continuation flags, and front-matter footnotes. Only the book-specific additions are documented below.

---

## `publication`

The publishing facts of the volume, distinct from `frontMatter` (the work's own title/authors) and `metadata` (the transcription run). Every field is optional; the whole object may be deleted.

```json
{
  "publisher": "Gregorian & Biblical Press",
  "publisherLocation": "Roma",
  "series": "Tesi Gregoriana. Serie Filosofia",
  "isbn": "978-88-7839-230-4",
  "copyrightYear": 2012,
  "copyrightHolder": "Pontificio Istituto Biblico",
  "imprimatur": "Vidimus et approbamus ad normam Statutorum..."
}
```

| Field | Type | Description |
|---|---|---|
| `publisher` | `string` | Publisher name as printed. |
| `publisherLocation` | `string` | Place of publication. |
| `series` | `string` | Series or collection, if any. |
| `isbn` | `string` | ISBN as printed, with hyphens. |
| `copyrightYear` | `integer` | Year of the copyright notice. |
| `copyrightHolder` | `string` | Holder of the copyright. |
| `edition` | `string` | Edition statement, if given. |
| `imprimatur` | `string` | Ecclesiastical/institutional approval notice as printed. |

---

## `structure` and `division`

`structure` is an array of top-level `division` nodes in reading order; each may nest `children`. A division describes a logical unit of the book and **points at** where it lives in `pages` — it does not contain the prose.

```json
{
  "id": "div-0007",
  "kind": "chapter",
  "number": "II",
  "title": "Aquinas’ Position on Natural Reason and the Ends of the Moral Virtues",
  "authors": [ { "name": "Dominic Farrell" } ],
  "startPageId": "page-0027",
  "startElementId": "heading-0014",
  "firstPageLabel": "67",
  "lastPageLabel": "102",
  "children": [ ... ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | yes | Unique monotonic ID, `div-NNNN`. Stable target for cross-references and citation. |
| `kind` | `string` (enum) | yes | Structural role — see the enum below. |
| `number` | `string` | no | Division number exactly as printed (`"I"`, `"2.1.3"`). Omitted for unnumbered divisions. |
| `title` | `string` | no | Division title, without its number. May contain inline formatting and footnote references. |
| `subtitle` | `string` | no | Division subtitle, if any. |
| `authors` | `[person]` | no | Contributors to this division. Empty for a monograph; populated for the chapters of an **edited volume**. |
| `startPageId` | `string` | no | `id` of the page where the division begins. |
| `startElementId` | `string` | no | `id` of the element (usually its heading) where the division begins. Omitted when there is no single anchoring element (e.g. a title page). |
| `firstPageLabel` | `string` | no | Printed page label where the division starts. Citation convenience. |
| `lastPageLabel` | `string` | no | Printed page label where the division ends. Omit when unknown (partial transcription). |
| `children` | `[division]` | no | Nested sub-divisions in reading order. |

### `kind` values

`half-title`, `title-page`, `copyright`, `dedication`, `epigraph`, `foreword`, `preface`, `contents`, `acknowledgements`, `introduction`, `part`, `chapter`, `section`, `subsection`, `conclusion`, `afterword`, `appendix`, `abbreviations`, `bibliography`, `glossary`, `index`, `notes`, `other`.

Use the most specific applicable value; `other` for anything unlisted.

---

## How the overlay relates to the pages

- **Single source of truth.** The prose lives once, in `pages`. `structure` only references it. There is no duplication of body text to drift out of sync.
- **The printed Table of Contents is content, not structure.** The TOC is reproducible front-matter prose on its own pages (a `contents` division). The `structure` outline is *derived* navigation metadata — ideally built from the in-body division headings and cross-checked against the printed TOC. Keep both.
- **Extent.** A division runs from its `startElementId` up to the element that begins the next division at the same or a shallower depth. `firstPageLabel`/`lastPageLabel` record the printed span for human citation.
- **Partial transcriptions.** `structure` need only cover the divisions that actually appear in the transcribed pages; a division still in progress may omit `lastPageLabel`.

## Citation and reproduction

- **Cite by page** using `pages[].pageLabel`; **cite by division** (Part, chapter, §) using a division's `number`/`title` and its `firstPageLabel`. Paragraph and footnote IDs remain available for finer citation.
- **Reproduce** by walking `structure` to emit `\part` / `\chapter` / `\section`, filling each from the referenced page elements, and emitting footnotes from the referenced footnote objects.

## Edited volumes

For an edited volume, put the volume editors in top-level `frontMatter.editors`, leave top-level `frontMatter.authors` empty, and give each chapter `division` its own `authors`. A monograph does the opposite: top-level `frontMatter.authors` holds the single author and divisions carry no `authors`.

## Quasi-article extraction

To use a chapter as a stand-alone article: take its `division` subtree and the slice of `pages` from `firstPageLabel`/`startPageId` through `lastPageLabel`. The result — pages with elements and footnotes, plus a front matter assembled from the division's `title`/`authors` — matches the [journal-article](../journal-article/README.md) shape, so the same downstream tooling (markdown stitching, footnote-integrity checking) applies unchanged.

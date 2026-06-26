# JSON Export Format Schema

This document defines the JSON schema produced by `PDFTranscriber`. The format is the serialization of the Swift `TranscribedDocument` type using `JSONEncoder` with ISO 8601 date encoding and sorted keys.

## Top-Level Structure  

```json
{
  "metadata": { ... },
  "frontMatter": { ... },
  "pages": [ ... ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `metadata` | `DocumentMetadata` | no | Information about the transcription run. May be omitted or deleted (e.g. for privacy) without affecting validity. |
| `frontMatter` | `FrontMatter` | no | The article's own title, author(s), and affiliation as printed. |
| `pages` | `[TranscribedPage]` | yes | Array of transcribed pages, in document order. |

Only `pages` is required. `metadata` describes the *transcription run*; `frontMatter` describes the *article's content*. Both are optional and independent of one another.

---

## `DocumentMetadata`

```json
{
  "sourceFile": "document.pdf",
  "totalPages": 42,
  "processingDate": "2026-04-07T07:41:51Z",
  "modelUsage": {
    "openai/gpt-4o": 10,
    "anthropic/claude-sonnet-4-20250514": 2
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `sourceFile` | `string` | no | Filename of the source PDF (basename, not a full path). |
| `totalPages` | `integer` | no | Number of pages that were transcribed. |
| `processingDate` | `string` | no | ISO 8601 timestamp (UTC) of when transcription ran. |
| `modelUsage` | `object` | no | Map of `"provider/model"` to the number of API calls made with that model. |

The entire `metadata` object is optional, and so is every field within it. Omit or delete any of them freely.

---

## `FrontMatter`

The article's own bibliographic information, as printed on the page. This captures title/author/affiliation in one reliable location instead of leaving them as untyped body paragraphs. Every field is optional and the whole object may be omitted.

```json
{
  "title": "The Multifarious Moral Object of Thomas Aquinas",
  "subtitle": "An Essay in Thomistic Action Theory",
  "authors": [
    {
      "name": "Kevin L. Flannery, S.J.",
      "affiliation": "Pontifical Gregorian University, Rome, Italy"
    }
  ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `string` | no | Article title. May contain inline Markdown and `<sc>` tags. |
| `subtitle` | `string` | no | Article subtitle, if any. |
| `authors` | `[Author]` | no | Authors in the order printed. May be empty. |

### `Author`

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | yes | Author's name as printed, in natural mixed case. May contain `<sc>` tags and inline footnote references. |
| `affiliation` | `string` | no | Institutional affiliation as printed. Authors who share one each carry their own copy. May contain inline footnote references. |

The article title belongs here, **not** in a level-1 `heading`. In-body headings (`heading` elements) are reserved for section headings within the body.

**Front-matter footnotes** (an author's `*` acknowledgement note, a dagger on the title, etc.) are *not* a separate field. They are ordinary footnote objects, stored on the page where they are printed, and anchored by an inline `[^fn-NNNN]` reference placed in the relevant front-matter field (usually `name`). See [Inline footnote references](#inline-footnote-references) below.

---

## `TranscribedPage`

```json
{
  "id": "page-0001",
  "pageLabel": "1",
  "runningHeader": "THE AMERICAN JOURNAL OF JURISPRUDENCE (1999)",
  "elements": [ ... ],
  "footnotes": [ ... ]
}
```

A page that could not be transcribed (when `skipFailedPages` is enabled):

```json
{
  "id": "page-0003",
  "pageLabel": "3",
  "elements": [],
  "footnotes": [],
  "skipped": true,
  "skipReason": "All models failed on page 3, region 1: content was filtered"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | yes | Unique monotonic ID. Format: `page-NNNN` (zero-padded to 4 digits, starting at `0001`). |
| `pageLabel` | `string` | yes | User-readable page label as printed on the physical page (e.g. `"35"`, `"iv"`, `"xii"`). Extracted by the AI model from the header or footer area when visible; falls back to `PDFPage.label` (typically 1-based index). May not be unique across the document (e.g. front matter and body may both have a page "1"). |
| `runningHeader` | `string` | no | Running header text if present on the page. Omitted (absent from JSON) if null. |
| `elements` | `[PageElement]` | yes | Array of body elements (paragraphs and headings) in reading order. May be empty. |
| `footnotes` | `[Footnote]` | yes | Array of footnotes in reading order. May be empty. |
| `skipped` | `boolean` | no | `true` if this page could not be transcribed and was recorded as a placeholder. Only present (and `true`) when `skipFailedPages` is enabled and the page failed. Omitted for normally transcribed pages. |
| `skipReason` | `string` | no | Human-readable error description. Only present when `skipped` is `true`. |

---

## `PageElement` (discriminated union)

Elements are serialized as a **discriminated union** using a `type` field. The `type` field determines which other fields are present.

### `type: "paragraph"`

```json
{
  "type": "paragraph",
  "id": "para-0003",
  "text": "Augustine held that the fact that an act is a lie...",
  "continuesFromPrevious": false,
  "continuesToNext": true
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `string` | yes | Always `"paragraph"`. |
| `id` | `string` | yes | Unique monotonic ID. Format: `para-NNNN`. |
| `text` | `string` | yes | Paragraph text. May contain inline Markdown formatting (`**bold**`, `*italic*`). |
| `continuesFromPrevious` | `boolean` | yes | `true` if this paragraph is a continuation of the last paragraph on the preceding page. |
| `continuesToNext` | `boolean` | yes | `true` if this paragraph continues on the next page. |

### `type: "heading"`

```json
{
  "type": "heading",
  "id": "heading-0002",
  "level": 1,
  "text": "I. Augustine on Lying"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `string` | yes | Always `"heading"`. |
| `id` | `string` | yes | Unique monotonic ID. Format: `heading-NNNN`. |
| `level` | `integer` | yes | Heading level, 1-6. Level 1 is the document or article title, level 2 is a major section heading, etc. |
| `text` | `string` | yes | Heading text. May contain inline Markdown formatting. |

### `type: "blockQuote"`

```json
{
  "type": "blockQuote",
  "id": "quote-0001",
  "text": "For it is written: Thou shalt not bear false witness.",
  "continuesFromPrevious": false,
  "continuesToNext": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `string` | yes | Always `"blockQuote"`. |
| `id` | `string` | yes | Unique monotonic ID. Format: `quote-NNNN`. |
| `text` | `string` | yes | Block quote text. May contain inline Markdown formatting and `<sc>` tags. |
| `continuesFromPrevious` | `boolean` | yes | `true` if this block quote continues from the previous page. |
| `continuesToNext` | `boolean` | yes | `true` if this block quote continues on the next page. |

---

## `Footnote`

```json
{
  "id": "fn-0003",
  "marker": "2",
  "text": "See Boniface Ramsey, O.P., \"Two Traditions...\" *The Thomist* 48 (1985) 515-531.",
  "continuesFromPrevious": false,
  "continuesToNext": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | yes | Unique monotonic ID. Format: `fn-NNNN`. |
| `marker` | `string` | yes | The footnote marker as displayed in the source document (e.g. `"1"`, `"*"`, `"†"`). This is the user-readable label and may not be unique across the document. |
| `text` | `string` | yes | Footnote body text. May contain inline Markdown formatting. |
| `continuesFromPrevious` | `boolean` | yes | `true` if this footnote continues from the previous page. |
| `continuesToNext` | `boolean` | yes | `true` if this footnote continues on the next page. |

### Footnotes split across a page boundary

A footnote whose text begins at the foot of page N and finishes at the top of page N+1 is recorded as **two footnote objects**, each with its own `id`:

- The fragment on page N has `continuesToNext: true`.
- The fragment on page N+1 has `continuesFromPrevious: true`.

Conventions for the split:

- The **continuation fragment repeats the `marker`** of the fragment it continues. A continuation has no separately printed marker, so reusing the original keeps the pair recognizable and the marker field populated.
- Only the **first** fragment is the target of an inline `[^fn-...]` reference. The reference always points at the `id` of the first fragment (where the marker is actually printed in the body), never the continuation.

Downstream tools join the fragments using the flags, exactly as with paragraphs.

---

## ID System

All IDs are **monotonic** and **globally unique** within a document. They are assigned after all pages are sorted into final document order.

| Prefix | Format | Example | Used for |
|---|---|---|---|
| `page` | `page-NNNN` | `page-0001` | Pages |
| `para` | `para-NNNN` | `para-0012` | Paragraphs |
| `heading` | `heading-NNNN` | `heading-0003` | Headings |
| `quote` | `quote-NNNN` | `quote-0001` | Block quotes |
| `fn` | `fn-NNNN` | `fn-0007` | Footnotes |

Each prefix has its own independent counter starting at `0001`. IDs are zero-padded to 4 digits.

---

## Continuation Flags

Paragraphs, block quotes, and footnotes carry two boolean flags that indicate when a single logical unit of running text has been split into more than one element:

- **`continuesFromPrevious: true`** — This element continues the preceding element of the same kind rather than starting a new one. When `false`, it begins a new logical paragraph (typically signalled in print by a first-line indent).
- **`continuesToNext: true`** — This element's text is continued by a following element of the same kind.

A split can be caused by two things:

1. **A page boundary.** The continued-from element is the last element of its kind on the preceding page, and the continuing element is the first on the next page.
2. **An intervening element on the same page.** Most commonly a block quote interrupts a paragraph: the running text resumes, un-indented, after the quote. The paragraph *before* the quote has `continuesToNext: true` and the paragraph *after* it has `continuesFromPrevious: true`; the block quote sits between them.

Consumers distinguish the two cases by checking whether the linked elements are on the same page (look at which page's array each lives in). The flags themselves carry the same meaning in both cases.

**This library does not stitch continuations.** Each page is self-contained. Downstream tools are responsible for joining split paragraphs, block quotes, and footnotes using these flags.

Typical continuation patterns:
- A paragraph split across pages 3-4: page 3's last paragraph has `continuesToNext: true`, page 4's first paragraph has `continuesFromPrevious: true`.
- A paragraph spanning pages 3-5: page 3 has `continuesToNext: true`, page 4 has both flags `true`, page 5 has `continuesFromPrevious: true`.
- A paragraph interrupted by a block quote on one page: the paragraph before the quote has `continuesToNext: true`, the paragraph after has `continuesFromPrevious: true`. A genuinely new (indented) paragraph after a quote has both `false`.
- Footnotes follow the same pattern across page boundaries.

---

## Text Formatting

All `text` fields may contain **inline Markdown** formatting and custom tags:
- `**bold**` for bold text
- `*italic*` for italic text
- `<sc>small caps</sc>` for small-caps text. The original mixed case is preserved as it would appear in normal typesetting (e.g., `<sc>Joseph Boyle</sc>`, not `JOSEPH BOYLE`).
- `[^fn-NNNN]` for an **inline footnote reference** — the anchor point where a footnote attaches to the running text.

No block-level Markdown (lists, code blocks) is used within text fields. Block quotes are represented as their own element type (`"blockQuote"`), not as Markdown. The document structure is expressed through the JSON hierarchy, not through Markdown.

### Inline footnote references

A footnote's *position* in the text is recorded by an inline reference token, written in the running text exactly where the marker appears:

```json
{
  "type": "paragraph",
  "id": "para-0002",
  "text": "...a much more complicated affair.[^fn-0001] Of course, the more general virtues...",
  "continuesFromPrevious": false,
  "continuesToNext": true
}
```

- The token is `[^` + the target footnote's **`id`** + `]` — e.g. `[^fn-0001]`. It references the footnote `id` rather than its `marker` because markers (`"1"`, `"*"`, …) are not unique across the document, whereas `id`s are.
- The symbol to *display* at that point is the referenced footnote's `marker`.
- A footnote may be referenced from any text field: an element's `text` (paragraph, heading, block quote), another footnote's `text`, or a **front-matter field** (`frontMatter.title`, `subtitle`, and each author's `name` / `affiliation`). The footnote object itself always lives in the `footnotes` array of the page where it is printed, which need not be the same page — or even the same region — as the reference.
- This decouples three concerns that used to be conflated: **where** a note is anchored (the inline token), **what symbol** it shows (the `marker`), and **what it says** (the `text`).

#### Front-matter footnotes vs. numbered body footnotes

Because the *origin* of a reference is recorded, the two kinds of footnote stay cleanly separable:

- A footnote anchored from a **front-matter** field is a front-matter note (e.g. an author acknowledgement). For **citation** purposes these are normally ignored — they fall outside the numbered series you cite by number.
- A footnote anchored from **body** text is a normal numbered note, citable by its `marker`.

This means a single representation serves both use cases: front-matter notes are preserved in full (marker, text, position) for faithful **reproduction**, yet never pollute the numbered footnote sequence used for **citation**. There is no separate "author note" field — one footnote mechanism covers everything.

---

## Encoding Details

- **Encoder**: `JSONEncoder` with `.iso8601` date encoding strategy and `.sortedKeys` output formatting (when pretty-printed).
- **Decoder**: `JSONDecoder` with `.iso8601` date decoding strategy.
- **Null handling**: Null/nil fields are omitted from the JSON output entirely (e.g. `runningHeader` is absent rather than `null` when there is no running header).
- **Key ordering**: When pretty-printed, keys within each object are sorted alphabetically. This is a property of the encoder, not the schema — consumers must not depend on key order.
- **Character encoding**: UTF-8.

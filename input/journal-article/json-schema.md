# JSON Export Format Schema

This document defines the JSON schema produced by `PDFTranscriber`. The format is the serialization of the Swift `TranscribedDocument` type using `JSONEncoder` with ISO 8601 date encoding and sorted keys.

## Top-Level Structure  

```json
{
  "metadata": { ... },
  "pages": [ ... ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `metadata` | `DocumentMetadata` | yes | Information about the transcription run. |
| `pages` | `[TranscribedPage]` | yes | Array of transcribed pages, in document order. |

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
| `sourceFile` | `string` | yes | Filename of the source PDF (basename, not a full path). |
| `totalPages` | `integer` | yes | Number of pages that were transcribed. |
| `processingDate` | `string` | yes | ISO 8601 timestamp (UTC) of when transcription ran. |
| `modelUsage` | `object` | yes | Map of `"provider/model"` to the number of API calls made with that model. |

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

Paragraphs and footnotes carry two boolean flags to indicate content that spans page boundaries:

- **`continuesFromPrevious: true`** — This element is a continuation of the last element of the same kind on the preceding page.
- **`continuesToNext: true`** — This element continues on the next page.

**This library does not stitch continuations.** Each page is self-contained. Downstream tools are responsible for joining split paragraphs and footnotes using these flags.

Typical continuation patterns:
- A paragraph split across pages 3-4: page 3's last paragraph has `continuesToNext: true`, page 4's first paragraph has `continuesFromPrevious: true`.
- A paragraph spanning pages 3-5: page 3 has `continuesToNext: true`, page 4 has both flags `true`, page 5 has `continuesFromPrevious: true`.
- Footnotes follow the same pattern.

---

## Text Formatting

All `text` fields may contain **inline Markdown** formatting and custom tags:
- `**bold**` for bold text
- `*italic*` for italic text
- `<sc>small caps</sc>` for small-caps text. The original mixed case is preserved as it would appear in normal typesetting (e.g., `<sc>Joseph Boyle</sc>`, not `JOSEPH BOYLE`).

No block-level Markdown (lists, code blocks) is used within text fields. Block quotes are represented as their own element type (`"blockQuote"`), not as Markdown. The document structure is expressed through the JSON hierarchy, not through Markdown.

---

## Encoding Details

- **Encoder**: `JSONEncoder` with `.iso8601` date encoding strategy and `.sortedKeys` output formatting (when pretty-printed).
- **Decoder**: `JSONDecoder` with `.iso8601` date decoding strategy.
- **Null handling**: Null/nil fields are omitted from the JSON output entirely (e.g. `runningHeader` is absent rather than `null` when there is no running header).
- **Key ordering**: When pretty-printed, keys within each object are sorted alphabetically. This is a property of the encoder, not the schema — consumers must not depend on key order.
- **Character encoding**: UTF-8.

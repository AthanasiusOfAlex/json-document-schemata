# Annotated JSON Example

This is a complete, annotated example of the JSON export format, taken from a real transcription of pages 1-2 of an academic article. Comments (not valid JSON) are included inline for explanation.

See [json-schema.md](json-schema.md) for the formal schema definition.

```jsonc
{
  // Top-level: metadata + pages array
  "metadata": {
    "modelUsage": {
      "openai/gpt-5.4-mini": 10       // 10 API calls made with this model
    },
    "processingDate": "2026-04-06T19:49:22Z",  // ISO 8601, UTC
    "sourceFile": "boyle.1999.pdf",             // basename only
    "totalPages": 5
  },
  "pages": [
    {
      // --- Page 1 ---
      "id": "page-0001",           // monotonic, globally unique
      "pageLabel": "1",            // as printed on the physical page
      // No "runningHeader" key — omitted because this page has none

      "elements": [
        {
          // A heading: uses "type" discriminator, has "level" instead of continuation flags
          "type": "heading",
          "id": "heading-0001",
          "level": 1,
          "text": "THE ABSOLUTE PROHIBITION OF LYING AND THE ORIGINS OF THE CASUISTRY OF MENTAL RESERVATION"
        },
        {
          // A paragraph: uses "type" discriminator, has continuation flags
          // Small-caps text uses <sc> tags with original mixed case preserved
          "type": "paragraph",
          "id": "para-0001",
          "text": "<sc>Joseph Boyle</sc>*",
          "continuesFromPrevious": false,
          "continuesToNext": false
        },
        {
          "type": "paragraph",
          "id": "para-0002",
          "text": "St. Augustine seems to have been the first important moralist...",
          "continuesFromPrevious": false,
          "continuesToNext": false
        },
        {
          // This paragraph continues on the next page
          "type": "paragraph",
          "id": "para-0003",
          "text": "First, perhaps because of the continuing influence of Western Christianity...",
          "continuesFromPrevious": false,
          "continuesToNext": true        // <-- continues on page 2
        }
      ],

      "footnotes": [
        {
          // Footnotes have a "marker" (the printed symbol) instead of "type"/"level"
          "id": "fn-0001",
          "marker": "*",                 // as displayed in the document
          "text": "An earlier version of this paper was presented...",
          "continuesFromPrevious": false,
          "continuesToNext": false
        }
      ]
    },
    {
      // --- Page 2 ---
      "id": "page-0002",
      "pageLabel": "2",
      "runningHeader": "THE AMERICAN JOURNAL OF JURISPRUDENCE (1999)",  // present on this page

      "elements": [
        {
          // Continuation of para-0003 from page 1
          "type": "paragraph",
          "id": "para-0004",            // gets its own unique ID
          "text": "Kant's. This body of moral analysis is a likely source...",
          "continuesFromPrevious": true, // <-- continued from page 1
          "continuesToNext": false
        },
        {
          "type": "paragraph",
          "id": "para-0005",
          "text": "Second, the general approach to the moral evaluation...",
          "continuesFromPrevious": false,
          "continuesToNext": false
        },
        {
          // A block quote: extended quotation set off from surrounding text
          "type": "blockQuote",
          "id": "quote-0001",
          "text": "\"Thou shalt not bear false witness\" (Exodus 20:16).",
          "continuesFromPrevious": false,
          "continuesToNext": false
        },
        {
          // A second heading on this page — counter increments independently
          "type": "heading",
          "id": "heading-0002",
          "level": 1,
          "text": "I. Augustine on Lying"
        },
        {
          "type": "paragraph",
          "id": "para-0006",
          "text": "To all appearances, Augustine came to the conclusion...",
          "continuesFromPrevious": false,
          "continuesToNext": false
        }
      ],

      "footnotes": [
        {
          "id": "fn-0002",
          "marker": "1",               // numeric marker — note fn counter is independent
          "text": "For a useful introduction to this literature, see Johann P. Sommerville...",
          "continuesFromPrevious": false,
          "continuesToNext": false
        },
        {
          "id": "fn-0003",
          "marker": "2",
          "text": "See Boniface Ramsey, O.P., \"Two Traditions on Lying and Deception in the Ancient Church,\" *The Thomist* 48 (1985) 515-531.",
          "continuesFromPrevious": false,
          "continuesToNext": false
          // Note: *The Thomist* uses Markdown italic within the JSON string
        }
      ]
    }
  ]
}
```

## Key Observations

1. **ID counters are independent per prefix.** `para-0006`, `heading-0002`, `quote-0001`, and `fn-0003` can all coexist — each prefix (`para`, `heading`, `quote`, `fn`, `page`) has its own counter.

2. **Continuation pairs.** When a paragraph spans a page break, the last paragraph on page N has `continuesToNext: true` and the first paragraph on page N+1 has `continuesFromPrevious: true`. Each half gets its own unique ID. Stitching them is a downstream responsibility.

3. **`runningHeader` is omitted, not null.** If a page has no running header, the key is absent from the JSON entirely.

4. **Inline formatting in text fields.** Footnote fn-0003 above contains `*The Thomist*` — italic Markdown within the JSON string value. Para-0001 uses `<sc>Joseph Boyle</sc>` — small-caps tags with original mixed case preserved. Only inline formatting (`*italic*`, `**bold**`, `<sc>small caps</sc>`) is used; no block-level Markdown.

5. **`pageLabel` vs `id`.** The `pageLabel` is what appears on the printed page and can repeat (e.g. front matter "1" and body "1"). The `id` is always globally unique.

6. **Keys are sorted alphabetically** in pretty-printed output (a property of `JSONEncoder.sortedKeys`), but consumers must not depend on key order.

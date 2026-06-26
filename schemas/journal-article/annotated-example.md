# Annotated JSON Example

This is a complete, annotated example of the JSON export format, taken from a real transcription of pages 1-2 of an academic article. Comments (not valid JSON) are included inline for explanation.

See [README.md](README.md) for the formal schema definition, and
[v1/schema.json](v1/schema.json) for the machine-readable JSON Schema.

```jsonc
{
  // Top-level: optional metadata, optional frontMatter, required pages array
  "metadata": {                              // describes the transcription RUN (all optional)
    "modelUsage": {
      "openai/gpt-5.4-mini": 10              // 10 API calls made with this model
    },
    "processingDate": "2026-04-06T19:49:22Z",  // ISO 8601, UTC
    "sourceFile": "boyle.1999.pdf",             // basename only
    "totalPages": 5
  },
  "frontMatter": {                           // describes the ARTICLE itself (all optional)
    "title": "The Absolute Prohibition of Lying and the Origins of the Casuistry of Mental Reservation",
    "authors": [
      {
        // The "*" author note is a real footnote (fn-0001, on page 1), anchored
        // here by an inline reference. Natural mixed case, not ALL CAPS.
        "name": "Joseph Boyle[^fn-0001]"
      }
    ]
  },
  "pages": [
    {
      // --- Page 1 ---
      "id": "page-0001",           // monotonic, globally unique
      "pageLabel": "1",            // as printed on the physical page
      // No "runningHeader" key — omitted because this page has none

      "elements": [
        // Note: the title and author are NOT here — they live in frontMatter above.
        {
          // A paragraph: uses "type" discriminator, has continuation flags
          "type": "paragraph",
          "id": "para-0001",
          "text": "St. Augustine seems to have been the first important moralist...",
          "continuesFromPrevious": false,
          "continuesToNext": false
        },
        {
          // This paragraph continues on the next page
          "type": "paragraph",
          "id": "para-0002",
          "text": "First, perhaps because of the continuing influence of Western Christianity...",
          "continuesFromPrevious": false,
          "continuesToNext": true        // <-- continues on page 2
        }
      ],

      "footnotes": [
        {
          // The author's "*" note: a normal footnote object, printed on this page,
          // anchored from frontMatter.authors[0].name above. Because its reference
          // originates in front matter, it is a front-matter note, not a numbered
          // body note — citation tools ignore it; reproduction tools keep it.
          "id": "fn-0001",
          "marker": "*",
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
          // Continuation of para-0002 from page 1
          "type": "paragraph",
          "id": "para-0003",            // gets its own unique ID
          "text": "Kant's. This body of moral analysis is a likely source...",
          "continuesFromPrevious": true, // <-- continued from page 1
          "continuesToNext": false
        },
        {
          "type": "paragraph",
          "id": "para-0004",
          // [^fn-0001] is an inline footnote reference: it anchors footnote fn-0001
          // at this exact point. The symbol shown is that footnote's "marker" ("1").
          "text": "Second, the general approach to the moral evaluation of action found in this literature...[^fn-0002]",
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
          // An in-body section heading (the article title is in frontMatter, not here)
          "type": "heading",
          "id": "heading-0001",
          "level": 1,
          "text": "I. Augustine on Lying"
        },
        {
          "type": "paragraph",
          "id": "para-0005",
          "text": "To all appearances, Augustine came to the conclusion...[^fn-0003]",
          "continuesFromPrevious": false,
          "continuesToNext": false
        }
      ],

      "footnotes": [
        {
          "id": "fn-0002",               // target of the [^fn-0002] reference above
          "marker": "1",                 // the printed symbol (fn counter is independent)
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

1. **`metadata` and `frontMatter` are separate and both optional.** `metadata` is about the *transcription run* (which models, when, source file); `frontMatter` is about the *article* (title, authors, affiliation). Either may be omitted or deleted; only `pages` is required.

2. **Title and author live in `frontMatter`, not in the body.** The article title is `frontMatter.title`, never a level-1 `heading`. `heading` elements are reserved for in-body section headings like "I. Augustine on Lying".

3. **Front-matter footnotes are ordinary footnotes.** The author's "*" note is a normal `footnote` object (`fn-0001`) on the page where it prints, anchored by a `[^fn-0001]` reference inside `frontMatter.authors[0].name`. There is no separate "note" field. Because its reference originates in front matter, it is recognizably a front-matter note: it keeps its marker and position for **reproduction**, yet stays out of the numbered series used for **citation**.

4. **ID counters are independent per prefix.** `para-0005`, `heading-0001`, `quote-0001`, and `fn-0003` can all coexist — each prefix (`para`, `heading`, `quote`, `fn`, `page`) has its own counter starting at `0001`.

5. **Continuation pairs.** When a paragraph spans a page break, the last paragraph on page N has `continuesToNext: true` and the first paragraph on page N+1 has `continuesFromPrevious: true`. The same flags also link a paragraph split by an intervening block quote on a single page. Each half gets its own unique ID; stitching is a downstream responsibility.

6. **Inline footnote references.** `[^fn-0001]` inside a `text` field marks *where* a footnote attaches. It targets the footnote's `id` (unique), while the displayed symbol comes from that footnote's `marker` (not unique). This keeps *position*, *symbol*, and *content* independent.

7. **`runningHeader` is omitted, not null.** If a page has no running header, the key is absent from the JSON entirely.

8. **`pageLabel` vs `id`.** The `pageLabel` is what appears on the printed page and can repeat (e.g. front matter "1" and body "1"). The `id` is always globally unique.

9. **Keys are sorted alphabetically** in pretty-printed output (a property of `JSONEncoder.sortedKeys`), but consumers must not depend on key order.

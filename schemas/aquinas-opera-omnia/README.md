# Thomistic Aquinas Opera Omnia JSON Schema

This schema provides a rigorous, machine-readable architecture for storing the complete works of St. Thomas Aquinas in Latin. It harmonizes the logical flow of the scholastic method with the precise typographical boundaries of physical critical editions.

## Core Architecture

The schema uses a unified, recursive tree structure with four layers:

1. **`work_metadata`**: Establishes the work and the critical edition used (e.g., *Editio Leonina* or *Marietti*).
2. **`structural_node`**: A recursive object defining both the hierarchical structure of the work (e.g., *Pars -> Quaestio -> Articulus*) and the scholastic function of the text (e.g., *respondeo*, *sed contra*). This unified model means every division--from a *Pars* down to a *respondeo*--is represented by the same object type.
3. **`paragraph`**: A logical paragraph of text within a leaf-level node. Its Latin text is divided into segments.
4. **`text_segment`**: The text printed at one citable location in the critical edition: a line where the edition numbers its lines, otherwise a page (and column).

The current version is **v1.3** (`v1.3/schema.json`). `v1.2/`, `v1.1/` and `v1/` are kept unchanged so their `$id`s stay stable; see *Changes from v1.2*, *Changes from v1.1* and *Changes from v1* below.

### The Unified Node Model

All levels of the hierarchy use `structural_node`. The `node_type` enum is divided into two groups:

**Structural types** define the divisions of a work:
- `pars`, `liber`, `distinctio`, `quaestio`, `articulus`, `quaestiuncula`, `capitulum`, `tractatus`, `lectio`, `sectio`

**Scholastic function types** define the rhetorical role of the text:
- `prooemium`, `argumentum`, `sed_contra`, `respondeo`, `ad_argumentum`, `textus_expositus`, `divisio_textus`, `expositio`, `conclusio`, `textus`

Structural nodes contain `children`; scholastic function nodes contain `paragraphs`. The schema enforces this distinction with `if/then` validation constraints.

The special case is **`prooemium`**, which can serve either role: a section-level *prooemium* (e.g., the introduction to the *Prima Pars*) is a structural node with children, while a text-level *prooemium* within an *articulus* is a leaf node with paragraphs. The tree position disambiguates. A prooemium may also hold both, its paragraphs first: the prologue of the first book of the commentary on the Sentences is Thomas's sermon (paragraphs), then the prologue's own question and the exposition of Lombard's prologue (children).

## Typographical vs. Semantic Structure (The Segment Array)

Scholarly citation requires exact page (and, where printed, line) numbers, but page breaks often interrupt the semantic flow of Aquinas's arguments. To preserve both, the `paragraph` holds a logical paragraph and its `segments` array divides that text where the physical location changes.

### The segment rule
**A segment is the longest run of a paragraph's text that shares one complete citable location.**
* In an edition that numbers its lines (the modern Leonine volumes), the location includes the line, so **each segment is one printed line**, and `edition_location.line` gives its number.
* In an edition without line numbers (the Leonine *Summa*, vols. 4–12), the location is page and column, so a segment is everything in the paragraph that falls in one column of one page. `line` is omitted.

Array order is reading order. Segments never run backwards through the edition: (volume, page, column) never decrease in document order, and within one paragraph and column each `line` is greater than the last.

### The "Healed Word" convention
When a word is hyphenated across a line, column or page break (e.g., `philoso-` | `phicas`), the complete word (`philosophicas`) is placed entirely within the segment where the word *begins*. The next segment begins with the next whole word. A word is cited by the line it starts on, and full-text search is unaffected. A "word" here is any whitespace-delimited token, so punctuation and inline tags belong to the word they touch (`III,`, `<i>ego`).

### Joining segments
Because every segment boundary falls between two words, **the paragraph is its segments joined with a single space**. To make this exact, `latin_text` is whitespace-normalized: words separated by single spaces, no leading or trailing space, no line breaks. The schema enforces this with the pattern `^\S+( \S+)*$`.

### Inline markup and `continued_markup`
`latin_text` may carry these inline tags:
* `<i>…</i>`: italics, which in the Leonine mark quotations;
* `<sc>…</sc>`: small capitals, used for incipits (*Sed contra*, *Respondeo*, *Ad primum*);
* `<lemma>…</lemma>`: in a commentary, the words of the commented text quoted in the exposition (the lemmata).

Every segment's markup is balanced, so a single line can be quoted or displayed by itself. When a tagged span crosses a segment boundary, it is closed at the end of the segment and reopened at the start of the next. The segment that was cut is flagged with `continued_markup`, listing the tags closed this way, outermost first:

```json
{ "latin_text": "libro Soliloquiorum: <i>verum est id</i>", "continued_markup": ["i"], "edition_location": { "volume": "22/1", "page": "6", "line": 151 } },
{ "latin_text": "<i>quod est</i>;", "edition_location": { "volume": "22/1", "page": "6", "line": 152 } }
```

To rebuild the paragraph: for each flagged segment, remove its closing tags at the end and the matching opening tags at the start of the next segment. Then join with a single space: `libro Soliloquiorum: <i>verum est id quod est</i>;`. The flag is what tells a cut span apart from two separate spans that happen to meet at a break; without it they would be merged and the difference lost. The last segment of a paragraph never carries the flag. [`scripts/aquinas_integrity.py`](../../scripts/aquinas_integrity.py) has the reference implementation (`join_segments`) and checks every flag against its text.

### Headings
Headings are part of the printed text and can be cited. A structural node may therefore carry `heading_segments`: the heading as printed (e.g. `ARTICULUS TERTIUS. UTRUM DEUS SIT.`), divided into segments by the same rules. `title_latin` stays as the normalized title used for display and indexing (`Utrum Deus sit`).

### Optional fields in `edition_location`
* **`column`**: Only present for multi-column editions (`"a"` or `"b"`). Omit entirely for single-column editions.
* **`line`**: Only present for editions that number their lines. It is the line number as printed, or counted from the printed marks where only every fifth line is numbered. The schema does not care whether the edition numbers lines per page or continuously through a chapter or article; record whatever the edition prints.

### Editorial IDs
An optional `editorial_id` field on the `paragraph` object captures structural additions by editors (e.g., "Marietti n. 45"). This sits at the paragraph level because editorial numbering systems (such as Marietti's) correspond to individual paragraphs.

### Citable units and `run_on`
Nodes are the units a reader cites: a reply is its own `ad_argumentum` even when it is one line ("Unde patet solutio ad tertium"), because it is cited as *ad 3*. Sometimes the printed edition does not give such a unit a paragraph of its own but runs it on at the end of the paragraph before, which may belong to another node (the Leonine prints ST I q.82 a.5's reply to the third objection at the end of the reply to the second). A node cannot hold half a paragraph, so the unit keeps its own paragraph, marked `"run_on": true`. The field is present only when true. To rebuild the printed paragraphs, join each `run_on` paragraph to the one before it in reading order with a single space; [`scripts/aquinas_integrity.py`](../../scripts/aquinas_integrity.py) has the reference implementation (`printed_paragraphs`). A reply that answers all the objections at once is one node numbered for all of them (`"number": "1-3"`); one that closes the respondeo ("Et per hoc patet responsio ad obiecta") belongs to the respondeo, where print has it.

## The Scholastic Function Types

Every leaf-level `structural_node` is categorized by its scholastic function:
* `prooemium`: Introductions and prologues.
* `argumentum`: Initial objections (*Videtur quod...*).
* `sed_contra`: Authoritative counter-statements (*Sed contra...*).
* `respondeo`: The master's definitive corpus/answer (*Respondeo dicendum...*).
* `ad_argumentum`: Replies to specific objections (*Ad primum...*).
* `textus_expositus`: The source text being commented on (in scriptural and Aristotelian commentaries).
* `divisio_textus`: Thomas's division of the text commented on (*Divisio textus*, in the commentary on the Sentences).
* `expositio`: The commentary or exposition on the source text.
* `conclusio`: Formal conclusions.
* `textus`: The author's own continuous text in a unit with no scholastic or expository division: a chapter of the *Summa contra Gentiles* or of an opusculum, a sermon, a prayer.

## Changes from v1.2

v1.3 is a strict superset of v1.2: every v1.2 document is valid under v1.3. It adds two node types, for the works beyond the scholastic articles and the commentaries, and one optional paragraph field:

* **`sectio`** (structural: `children` only): a division the other structural types do not name: an entry (*vox*) of the *Tabula libri Ethicorum*, a part of a sermon, a group of prayers.
* **`textus`** (function: `paragraphs` only): the author's own continuous text, where no function type fits: the chapters of the *Summa contra Gentiles* and of the opuscula, sermons, prayers. Before v1.3 such text could only be misnamed `expositio` or `prooemium`.
* **`run_on`** (on `paragraph`, `true` or absent): the printed edition runs this paragraph on from the one before; see *Citable units and `run_on`*.

See `v1.3/examples/scg-i-c1.json` (`textus`, with the verse the chapter expounds as `textus_expositus`), `v1.3/examples/tabula-sectio.json` (`sectio`) and `v1.3/examples/st-i-q82-a5-run-on.json` (`run_on`).

## Changes from v1.1

v1.2 is a strict superset of v1.1: every v1.1 document is valid under v1.2. It adds two node types for the commentary on the Sentences:

* **`quaestiuncula`** (structural: `children` only): the sub-question of an article. Each has its own objections, sed contra, respondeo and replies, so folding them into the article would merge several series of arguments.
* **`divisio_textus`** (function: `paragraphs` only): Thomas's division of the text he comments on ("Divisio textus"), which is not an exposition of its letter; `expositio` stays for the "Expositio textus".

The descriptions also name `<lemma>` among the inline tags of `latin_text`, and say that a `prooemium` may hold paragraphs, children or both. See `v1.2/examples/sentences-quaestiuncula.json`.

## Changes from v1

v1.1 is published as a new `$id` because it rejects some v1 documents:

* **Segment rule:** one segment per citable location, so one per line in line-numbered editions.
* **`line`** replaces `line_start` / `line_end`, which are now rejected. A segment is always a single line, so a range is never needed.
* **Joining:** segments are joined with a single space. `latin_text` must be whitespace-normalized; v1's trailing-space style (`"…via est "`) is no longer valid.
* **`continued_markup`** (new, optional) marks inline markup split across a segment boundary.
* **`heading_segments`** (new, optional) records the printed heading of a structural node and its location.
* **`minItems: 1`** on `segments`, `paragraphs` and `heading_segments`.
* **Ordering and markup checks** that need to compare neighbouring segments live in `scripts/aquinas_integrity.py` and run in CI.

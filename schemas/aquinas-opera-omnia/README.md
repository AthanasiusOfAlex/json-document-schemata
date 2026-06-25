# Thomistic Aquinas Opera Omnia JSON Schema

This schema provides a rigorous, machine-readable architecture for storing the complete works of St. Thomas Aquinas in Latin. It harmonizes the logical flow of the scholastic method with the precise typographical boundaries of physical critical editions.

## Core Architecture

The schema uses a unified, recursive tree structure with four layers:

1. **`work_metadata`**: Establishes the work and the critical edition used (e.g., *Editio Leonina* or *Marietti*).
2. **`structural_node`**: A recursive object defining both the hierarchical structure of the work (e.g., *Pars -> Quaestio -> Articulus*) and the scholastic function of the text (e.g., *respondeo*, *sed contra*). This unified model means every division--from a *Pars* down to a *respondeo*--is represented by the same object type.
3. **`paragraph`**: A logical paragraph of text within a leaf-level node. Contains the actual Latin text, split into segments at page boundaries.
4. **`text_segment`**: A fragment of text corresponding to a single physical page (and column) in the critical edition.

### The Unified Node Model

All levels of the hierarchy use `structural_node`. The `node_type` enum is divided into two groups:

**Structural types** define the divisions of a work:
- `pars`, `liber`, `distinctio`, `quaestio`, `articulus`, `capitulum`, `tractatus`, `lectio`

**Scholastic function types** define the rhetorical role of the text:
- `prooemium`, `argumentum`, `sed_contra`, `respondeo`, `ad_argumentum`, `textus_expositus`, `expositio`, `conclusio`

Structural nodes contain `children`; scholastic function nodes contain `paragraphs`. The schema enforces this distinction with `if/then` validation constraints.

The special case is **`prooemium`**, which can serve either role: a section-level *prooemium* (e.g., the introduction to the *Prima Pars*) is a structural node with children, while a text-level *prooemium* within an *articulus* is a leaf node with paragraphs. The tree position disambiguates.

## Typographical vs. Semantic Structure (The Segment Array)

Scholarly citation requires exact page numbers, but page breaks often interrupt the semantic flow of Aquinas's arguments. To preserve both:
* The `paragraph` encapsulates a logical paragraph of text.
* The `segments` array within each paragraph divides that text exactly where the physical page or column ends.
* **Concatenation:** To read the full paragraph, an application simply joins the `latin_text` strings within the `segments` array.

### The "Healed Word" Convention
When a word is hyphenated across a page or column break (e.g., `philoso-` [page 6] `phicas` [page 7]), this database adopts the "Healed Word" convention to preserve full-text searchability. The complete word (`philosophicas`) is placed entirely within the segment where the word *begins*. The subsequent segment begins with the next whole word.

### Optional Fields in `edition_location`
* **`column`**: Only present for multi-column editions (e.g., `"a"` or `"b"`). Omit entirely for single-column editions.
* **`line_start`** and **`line_end`**: Optional, since not all editions feature line numbers.

### Editorial IDs
An optional `editorial_id` field on the `paragraph` object captures structural additions by editors (e.g., "Marietti n. 45"). This sits at the paragraph level because editorial numbering systems (such as Marietti's) correspond to individual paragraphs.

## The Scholastic Function Types

Every leaf-level `structural_node` is categorized by its scholastic function:
* `prooemium`: Introductions and prologues.
* `argumentum`: Initial objections (*Videtur quod...*).
* `sed_contra`: Authoritative counter-statements (*Sed contra...*).
* `respondeo`: The master's definitive corpus/answer (*Respondeo dicendum...*).
* `ad_argumentum`: Replies to specific objections (*Ad primum...*).
* `textus_expositus`: The source text being commented on (in scriptural and Aristotelian commentaries).
* `expositio`: The commentary or exposition on the source text.
* `conclusio`: Formal conclusions.

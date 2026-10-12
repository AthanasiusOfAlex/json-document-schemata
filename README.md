# JSON Document Schemata

Canonical [JSON Schema](https://json-schema.org/) definitions for validating
structured academic documents — the Latin corpus of St. Thomas Aquinas and
transcribed contemporary scholarship.

The schemata are published via GitHub Pages and can be referenced directly by
their `$id`:

> **<https://athanasiusofalex.github.io/json-document-schemata/>**

## Schemata

All schemata are written against JSON Schema **draft 2020-12**.

| Schema | Canonical `$id` |
|---|---|
| **Aquinas Opera Omnia** | `…/schemas/aquinas-opera-omnia/v1.3/schema.json` (current; `v1.2/`, `v1.1/` and `v1/` superseded) |
| **Journal Article** (PDFTranscriber) | `…/schemas/journal-article/v1/schema.json` |
| **Academic Book** (PDFTranscriber) | `…/schemas/book/v1/schema.json` |
| **Transcription Core** (shared) | `…/schemas/shared/transcription-core.json` |
| **Citation** (shared) | `…/schemas/shared/citation.json` |

(Each `$id` is prefixed with the site root above.)

### Aquinas Opera Omnia

A recursive tree modelling the complete Latin works of Aquinas. A single
`structural_node` type expresses both the hierarchical divisions of a work
(*pars → quaestio → articulus*, the *quaestiuncula* of the commentary on the
Sentences, and a generic *sectio*) and the scholastic function of the text (*argumentum*,
*sed contra*, *respondeo*, *ad argumentum*, *divisio textus*, and *textus* for continuous
text such as a chapter of the Summa contra Gentiles, …). Structural nodes
contain `children`; function nodes contain `paragraphs`, and the schema enforces
that distinction with `if`/`then` constraints. Each paragraph (and each printed
heading) is split into `segments`, one per citable location: one per line where
the edition numbers its lines, otherwise one per page/column. Joining the
segments with a single space gives back the paragraph exactly, so citation down
to the line is preserved alongside semantic flow. Nodes are the units a reader
cites; where the printed edition runs a cited unit on in the paragraph before (a short
reply), its paragraph is marked `run_on`, so print's paragraphs can be rebuilt.

See [schemas/aquinas-opera-omnia/README.md](schemas/aquinas-opera-omnia/README.md)
for the full design notes.

### Journal Article (PDFTranscriber `TranscribedDocument`)

The JSON serialization produced by `PDFTranscriber`: an optional `metadata`
object, optional `frontMatter`, plus an ordered `pages` array. Each page carries
body `elements` — a discriminated union of `paragraph`, `heading`, and
`blockQuote` (keyed on a `type` field) — and `footnotes`. Paragraphs, block
quotes, and footnotes carry `continuesFromPrevious` / `continuesToNext` flags for
content that spans page breaks (or an intervening block quote); inline
`[^fn-NNNN]` references anchor footnotes within text. The page-level definitions
live in **Transcription Core** (below). The schema is **permissive** (it does not
forbid unknown properties), so new fields can be added by the producer without
breaking validation.

See [schemas/journal-article/README.md](schemas/journal-article/README.md)
for the prose specification and
[schemas/journal-article/annotated-example.md](schemas/journal-article/annotated-example.md)
for an annotated example.

### Academic Book (PDFTranscriber)

A transcribed monograph or edited volume. It reuses the journal article's
page-primary model (the same shared page/element/footnote definitions) and adds
two things on top of the page spine: a `publication` object (publisher, ISBN,
copyright, series) and a `structure` overlay — a tree of `division` nodes (front
matter, parts, chapters, sections, back matter) that references into the pages by
`id` rather than holding prose. Any single division can therefore be sliced out
with the page range it spans as a self-contained "quasi-article". Divisions carry
their own `authors` for edited volumes.

See [schemas/book/README.md](schemas/book/README.md) for the full design notes.

### Transcription Core (shared)

The page-level definitions shared by the Journal Article and Academic Book
schemas — `documentMetadata`, `frontMatter`, `person`, `page`, `paragraph`,
`heading`, `blockQuote`, and `footnote`. A definitions library referenced via
`$ref`; not a standalone document schema.

### Citation (shared)

A small bibliographic-reference schema intended for reuse via `$ref`. It is not
currently referenced by any document schema, but is kept as a stub.

## Repository layout

```
schemas/
  aquinas-opera-omnia/
    README.md            # design notes
    v1/                  # superseded by v1.1; kept so its $id stays stable
      schema.json
      examples/          # instances that MUST validate
    v1.1/
      schema.json
      examples/
  journal-article/
    README.md            # prose specification of the format
    annotated-example.md # worked example with inline commentary
    v1/
      schema.json
      examples/
  book/
    README.md            # design notes for the academic-book schema
    v1/
      schema.json
      examples/
  shared/
    transcription-core.json  # page-level $defs shared across document types
    citation.json
scripts/
  validate.py            # validates every example against its schema
  footnote_integrity.py  # advisory footnote/reference consistency checks
  aquinas_integrity.py   # Aquinas segment markup and ordering checks
index.html               # GitHub Pages landing page
```

## Versioning

Schemata are versioned by directory (`/v1/`, `/v1.1/`). Backwards-incompatible changes are
published under a **new** version directory rather than edited in place — an
existing `$id` always denotes the same schema.

## Validation

[`scripts/validate.py`](scripts/validate.py) discovers every `schema.json`,
selects the correct validator for its declared draft, and checks every JSON file
in the adjacent `examples/` directory against it.

```bash
python -m venv .venv
source .venv/bin/activate
pip install jsonschema referencing
python scripts/validate.py
```

[`scripts/footnote_integrity.py`](scripts/footnote_integrity.py) adds an advisory
pass that the JSON Schema cannot express: it checks that inline `[^fn-NNNN]`
references and the footnotes they anchor are mutually consistent (each reference
resolves to exactly one footnote, markers run in order, page-split footnotes are
paired). Findings are split into structural `ERROR`s (which fail the run) and
`WARN`s tolerated in messy or partial transcriptions.

[`scripts/aquinas_integrity.py`](scripts/aquinas_integrity.py) does the same for
Aquinas documents. It checks that inline markup is balanced in each segment and
that every `continued_markup` flag matches its text. It also checks that segments
never run backwards through the edition (volume, page, column, line). Pass it
file paths to check generated output, e.g. a scraper run.

All three scripts run in CI on every push and pull request to `main`
(see [.github/workflows/ci.yml](.github/workflows/ci.yml)). The `examples/`
folders double as the test suite: every file there is expected to validate.

## License

Released under the [MIT License](LICENSE).

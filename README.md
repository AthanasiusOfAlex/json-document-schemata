# JSON Document Schemata

Canonical [JSON Schema](https://json-schema.org/) definitions for validating
structured academic documents — the Latin corpus of St. Thomas Aquinas and
transcribed contemporary scholarship.

The schemata are published via GitHub Pages and can be referenced directly by
their `$id`:

> **<https://athanasiusofalex.github.io/json-document-schemata/>**

## Schemata

| Schema | Draft | Canonical `$id` |
|---|---|---|
| **Aquinas Opera Omnia** | draft-07 | `…/schemas/aquinas-opera-omnia/v1/schema.json` |
| **Journal Article** (PDFTranscriber) | 2020-12 | `…/schemas/journal-article/v1/schema.json` |
| **Citation** (shared) | 2020-12 | `…/schemas/shared/citation.json` |

(Each `$id` is prefixed with the site root above.)

### Aquinas Opera Omnia

A recursive tree modelling the complete Latin works of Aquinas. A single
`structural_node` type expresses both the hierarchical divisions of a work
(*pars → quaestio → articulus*) and the scholastic function of the text
(*argumentum*, *sed contra*, *respondeo*, *ad argumentum*, …). Structural nodes
contain `children`; function nodes contain `paragraphs`, and the schema enforces
that distinction with `if`/`then` constraints. Each paragraph is split into
`segments` at physical page/column boundaries so that scholarly citation by
page number is preserved alongside semantic flow.

See [input/aquinas-opera-omnia/README.md](input/aquinas-opera-omnia/README.md)
for the full design notes.

### Journal Article (PDFTranscriber `TranscribedDocument`)

The JSON serialization produced by `PDFTranscriber`: a `metadata` object plus an
ordered `pages` array. Each page carries body `elements` — a discriminated union
of `paragraph`, `heading`, and `blockQuote` (keyed on a `type` field) — and
`footnotes`. Paragraphs, block quotes, and footnotes carry
`continuesFromPrevious` / `continuesToNext` flags for content that spans page
breaks. The schema is **permissive** (it does not forbid unknown properties), so
new fields can be added by the producer without breaking validation.

See [input/journal-article/json-schema.md](input/journal-article/json-schema.md)
for the prose specification and
[input/journal-article/json-example-annotated.md](input/journal-article/json-example-annotated.md)
for an annotated example.

### Citation (shared)

A small bibliographic-reference schema intended for reuse via `$ref`. It is not
currently referenced by either document schema, but is kept as a stub.

## Repository layout

```
schemas/
  aquinas-opera-omnia/v1/
    schema.json
    examples/            # instances that MUST validate
  journal-article/v1/
    schema.json
    examples/
  shared/
    citation.json
scripts/
  validate.py            # validates every example against its schema
input/                   # source material & human-readable documentation
index.html               # GitHub Pages landing page
```

## Versioning

Schemata are versioned by directory (`/v1/`). Backwards-incompatible changes are
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

The same script runs in CI on every push and pull request to `main`
(see [.github/workflows/ci.yml](.github/workflows/ci.yml)). The `examples/`
folders double as the test suite: every file there is expected to validate.

## License

No license has been chosen yet. Until one is added, default copyright applies.

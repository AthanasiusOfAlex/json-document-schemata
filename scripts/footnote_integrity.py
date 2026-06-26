#!/usr/bin/env python3
"""Advisory footnote-integrity checks for transcribed-document JSON.

Schema validation (``validate.py``) proves a document is *well-formed*. This
script checks something the JSON Schema cannot: that footnotes and the inline
``[^fn-NNNN]`` references that anchor them are mutually *consistent*.

The checks are deliberately **flexible**. A transcription may be imperfect,
pages may be missing, and markers may be non-numeric (``*``, ``†``). Findings
are therefore split into two levels:

  * ``ERROR`` — a structural impossibility (e.g. two footnotes share an ``id``,
    or a reference matches more than one footnote). These fail the run.
  * ``WARN``  — something that is *usually* a mistake but legitimately occurs
    in messy or partial sources (a dangling reference, an unreferenced
    footnote, markers out of order). These are reported but never fail the run.

Usage::

    python scripts/footnote_integrity.py [FILE ...]

With no arguments it checks every ``*.json`` under ``schemas/**/examples/``.
Exit status is non-zero only if an ERROR was found.
"""

import json
import re
import sys
from pathlib import Path

REF_RE = re.compile(r"\[\^(fn-\d{4,})\]")
NUMERIC_RE = re.compile(r"\d+")


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def iter_text_fields(doc):
    """Yield ``(location, text)`` for every field that may contain references,
    in document reading order. Front-matter fields come first, since they
    precede the body."""
    fm = doc.get("frontMatter") or {}
    for key in ("title", "subtitle"):
        if isinstance(fm.get(key), str):
            yield f"frontMatter/{key}", fm[key]
    for role in ("authors", "editors"):
        for i, person in enumerate(fm.get(role, []) or []):
            if not isinstance(person, dict):
                continue
            for key in ("name", "affiliation"):
                if isinstance(person.get(key), str):
                    yield f"frontMatter/{role}[{i}]/{key}", person[key]
    yield from _iter_divisions(doc.get("structure", []) or [])
    for page in doc.get("pages", []):
        pid = page.get("id", "?")
        for el in page.get("elements", []):
            if isinstance(el, dict) and "text" in el:
                yield f"{pid}/{el.get('id', '?')}", el["text"]
        for fn in page.get("footnotes", []):
            yield f"{pid}/{fn.get('id', '?')}", fn.get("text", "")


def _iter_divisions(divisions):
    """Yield ``(location, text)`` for footnote-bearing fields of the book
    structure overlay (division titles and contributor names), recursively."""
    for div in divisions or []:
        if not isinstance(div, dict):
            continue
        did = div.get("id", "?")
        for key in ("title", "subtitle"):
            if isinstance(div.get(key), str):
                yield f"structure/{did}/{key}", div[key]
        for i, person in enumerate(div.get("authors", []) or []):
            if isinstance(person, dict) and isinstance(person.get("name"), str):
                yield f"structure/{did}/authors[{i}]/name", person["name"]
        yield from _iter_divisions(div.get("children", []))


def collect(doc):
    """Return footnotes (in document order) and references (in reading order)."""
    footnotes = []
    for page in doc.get("pages", []):
        pid = page.get("id", "?")
        for fn in page.get("footnotes", []):
            footnotes.append({**fn, "_page": pid})
    references = []
    for loc, text in iter_text_fields(doc):
        for m in REF_RE.finditer(text or ""):
            references.append((loc, m.group(1)))
    return footnotes, references


def check(doc):
    """Return ``(errors, warnings)`` lists of human-readable strings."""
    errors, warnings = [], []
    footnotes, references = collect(doc)

    by_id = {}
    for fn in footnotes:
        by_id.setdefault(fn["id"], []).append(fn)

    # ERROR: footnote ids must be globally unique.
    for fid, fns in by_id.items():
        if len(fns) > 1:
            errors.append(f"footnote id {fid} is defined {len(fns)} times")

    # References must resolve to exactly one footnote.
    ref_counts = {}
    for loc, fid in references:
        ref_counts[fid] = ref_counts.get(fid, 0) + 1
        matches = len(by_id.get(fid, []))
        if matches == 0:
            warnings.append(
                f"reference [^{fid}] at {loc} resolves to no footnote "
                f"(missing page or transcription gap?)"
            )
        elif matches > 1:
            errors.append(
                f"reference [^{fid}] at {loc} matches {matches} footnotes"
            )

    # Every primary footnote should be anchored exactly once.
    # Continuation fragments (continuesFromPrevious) are not separately anchored.
    for fn in footnotes:
        if fn.get("continuesFromPrevious"):
            continue
        count = ref_counts.get(fn["id"], 0)
        marker = fn.get("marker", "?")
        if count == 0:
            warnings.append(
                f"footnote {fn['id']} (marker {marker!r}) is never referenced"
            )
        elif count > 1:
            warnings.append(
                f"footnote {fn['id']} (marker {marker!r}) is referenced {count} times"
            )

    # Numeric markers of primary fragments should strictly increase in document order.
    last_val, last_id = None, None
    for fn in footnotes:
        if fn.get("continuesFromPrevious"):
            continue
        marker = fn.get("marker", "") or ""
        if not NUMERIC_RE.fullmatch(marker):
            continue  # leave non-numeric markers (*, †, a, b ...) alone
        val = int(marker)
        if last_val is not None and val <= last_val:
            warnings.append(
                f"marker order: {fn['id']} marker {val} does not increase "
                f"after {last_id} marker {last_val}"
            )
        last_val, last_id = val, fn["id"]

    # References, in reading order, should encounter numeric markers in ascending order.
    sequence = []
    for loc, fid in references:
        fns = by_id.get(fid)
        if fns and NUMERIC_RE.fullmatch(fns[0].get("marker", "") or ""):
            sequence.append((loc, int(fns[0]["marker"])))
    for (loc_a, a), (loc_b, b) in zip(sequence, sequence[1:]):
        if b < a:
            warnings.append(
                f"reference order: ref at {loc_b} (marker {b}) comes after "
                f"marker {a} at {loc_a}"
            )

    # Continuation pairing across page boundaries for footnotes.
    pages = doc.get("pages", [])
    for i, page in enumerate(pages):
        fns = page.get("footnotes", [])
        if fns and fns[-1].get("continuesToNext"):
            nxt = pages[i + 1].get("footnotes", []) if i + 1 < len(pages) else []
            if not (nxt and nxt[0].get("continuesFromPrevious")):
                warnings.append(
                    f"{page.get('id')}: last footnote has continuesToNext, but the "
                    f"next page's first footnote is not a continuation"
                )
        if fns and fns[0].get("continuesFromPrevious"):
            prev = pages[i - 1].get("footnotes", []) if i > 0 else []
            if not (prev and prev[-1].get("continuesToNext")):
                warnings.append(
                    f"{page.get('id')}: first footnote is a continuation, but the "
                    f"previous page's last footnote has no continuesToNext"
                )

    return errors, warnings


def main(argv):
    paths = argv[1:]
    if not paths:
        root = Path(__file__).resolve().parent.parent
        paths = sorted(
            str(p)
            for p in (root / "schemas").rglob("*.json")
            if "examples" in p.parts
        )

    ok = True
    for path in paths:
        errors, warnings = check(load(path))
        print(f"\n{path}")
        if not errors and not warnings:
            print("  [OK] footnote integrity clean")
        for w in warnings:
            print(f"  [WARN]  {w}")
        for e in errors:
            print(f"  [ERROR] {e}")
        if errors:
            ok = False

    if not ok:
        print("\nFootnote integrity: ERRORS found.")
        sys.exit(1)
    print("\nFootnote integrity: no errors.")


if __name__ == "__main__":
    main(sys.argv)

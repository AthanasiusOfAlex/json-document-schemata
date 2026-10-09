#!/usr/bin/env python3
"""Integrity checks for Aquinas Opera Omnia JSON (aquinas-opera-omnia/v1.1).

Schema validation (``validate.py``) proves each segment is *well-formed*. This
script checks what the JSON Schema cannot, because it needs to compare one
segment with the next:

  * inline markup (``<i>``, ``<sc>``) is balanced in every segment, and each
    ``continued_markup`` flag matches the tags it claims were split;
  * segments run forward through the edition (volume, page, column, line).

Findings are split into two levels:

  * ``ERROR`` — a structural impossibility (unbalanced markup, a flag that
    does not match the text, a location that runs backwards). These fail the
    run.
  * ``WARN``  — something that is *usually* a mistake: a skipped line number
    inside a paragraph. Reported, but never fails the run.

Locations that are not numeric (the scraper's ``"[PAGE]"`` placeholder, roman
numerals) are skipped by the ordering checks.

``join_segments`` is the reference implementation of the joining rule: undo
``continued_markup``, then join the segments with a single space.

Usage::

    python scripts/aquinas_integrity.py [FILE ...]

With no arguments it checks every example under
``schemas/aquinas-opera-omnia/*/examples/``. Exit status is non-zero only if
an ERROR was found.
"""

import json
import re
import sys
from pathlib import Path

TAG_RE = re.compile(r"<(/?)([a-z][a-z0-9]*)>")
INT_RE = re.compile(r"\d+")


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def markup_problem(text):
    """Return a description of the first markup imbalance in ``text``, or None."""
    stack = []
    for m in TAG_RE.finditer(text):
        closing, name = m.group(1), m.group(2)
        if not closing:
            stack.append(name)
        elif not stack or stack[-1] != name:
            return f"unexpected </{name}>"
        else:
            stack.pop()
    if stack:
        return "unclosed " + "".join(f"<{t}>" for t in stack)
    return None


def join_segments(segments):
    """Rebuild a paragraph (or heading) from its segments.

    For each segment flagged with ``continued_markup``, the closing tags at its
    end and the matching opening tags at the start of the next segment are
    removed; the segments are then joined with a single space. Raises
    ``ValueError`` if a flag does not match the text.
    """
    texts = [s["latin_text"] for s in segments]
    for i, seg in enumerate(segments):
        carried = seg.get("continued_markup") or []
        if not carried:
            continue
        if i + 1 == len(segments):
            raise ValueError("continued_markup on the last segment")
        closing = "".join(f"</{t}>" for t in reversed(carried))
        opening = "".join(f"<{t}>" for t in carried)
        if not texts[i].endswith(closing):
            raise ValueError(f"segment {i + 1} has continued_markup but does not end with {closing}")
        if not texts[i + 1].startswith(opening):
            raise ValueError(f"segment {i + 2} does not start with {opening} carried from segment {i + 1}")
        texts[i] = texts[i][: -len(closing)]
        texts[i + 1] = texts[i + 1][len(opening):]
    return " ".join(texts)


def iter_runs(nodes):
    """Yield ``(label, segments)`` for every heading and paragraph, in reading order."""
    for node in nodes or []:
        nid = node.get("node_id", "?")
        if node.get("heading_segments"):
            yield f"{nid} (heading)", node["heading_segments"]
        for para in node.get("paragraphs", []) or []:
            yield para.get("paragraph_id", f"{nid} (paragraph)"), para.get("segments", [])
        yield from iter_runs(node.get("children"))


def place(seg):
    """Return a comparable ``(volume, page, column)`` key, or None if not numeric."""
    loc = seg.get("edition_location") or {}
    volume = tuple(int(n) for n in INT_RE.findall(str(loc.get("volume", ""))))
    page = str(loc.get("page", ""))
    if not volume or not page.isdigit():
        return None
    return volume, int(page), loc.get("column") or ""


def describe(seg):
    loc = seg.get("edition_location") or {}
    parts = [f"vol. {loc.get('volume')}", f"p. {loc.get('page')}{loc.get('column', '')}"]
    if "line" in loc:
        parts.append(f"l. {loc['line']}")
    return ", ".join(parts)


def check(doc):
    """Return ``(errors, warnings)`` lists of human-readable strings."""
    errors, warnings = [], []
    last_place, last_where = None, None

    for label, segments in iter_runs(doc.get("body", [])):
        # Markup: each segment balanced, each flag consistent, the whole run balanced.
        for i, seg in enumerate(segments, 1):
            problem = markup_problem(seg.get("latin_text", ""))
            if problem:
                errors.append(f"{label} segment {i}: {problem}")
        try:
            problem = markup_problem(join_segments(segments))
            if problem:
                errors.append(f"{label}: rejoined text has {problem}")
        except ValueError as e:
            errors.append(f"{label}: {e}")

        # Location: (volume, page, column) never runs backwards in reading order.
        for i, seg in enumerate(segments, 1):
            here = place(seg)
            if here is None:
                continue
            if last_place is not None and here < last_place:
                errors.append(f"{label} segment {i} ({describe(seg)}) comes before {last_where}")
            last_place, last_where = here, f"{label} ({describe(seg)})"

        # Lines: within a run and a single column, each line follows the last.
        for i, (a, b) in enumerate(zip(segments, segments[1:]), 2):
            la = (a.get("edition_location") or {}).get("line")
            lb = (b.get("edition_location") or {}).get("line")
            if la is None or lb is None or place(a) is None or place(a) != place(b):
                continue
            if lb <= la:
                errors.append(f"{label} segment {i}: line {lb} does not follow line {la}")
            elif lb != la + 1:
                warnings.append(f"{label} segment {i}: line {lb} follows line {la} (missing line?)")

    return errors, warnings


def main(argv):
    paths = argv[1:]
    if not paths:
        root = Path(__file__).resolve().parent.parent
        paths = sorted(str(p) for p in (root / "schemas" / "aquinas-opera-omnia").glob("*/examples/*.json"))

    ok = True
    for path in paths:
        errors, warnings = check(load(path))
        print(f"\n{path}")
        if not errors and not warnings:
            print("  [OK] Aquinas integrity clean")
        for w in warnings:
            print(f"  [WARN]  {w}")
        for e in errors:
            print(f"  [ERROR] {e}")
        if errors:
            ok = False

    if not ok:
        print("\nAquinas integrity: ERRORS found.")
        sys.exit(1)
    print("\nAquinas integrity: no errors.")


if __name__ == "__main__":
    main(sys.argv)

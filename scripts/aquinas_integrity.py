#!/usr/bin/env python3
"""Integrity checks for Aquinas Opera Omnia JSON (aquinas-opera-omnia/v1.1 to v1.4).

Schema validation (``validate.py``) proves each segment is *well-formed*. This
script checks what the JSON Schema cannot, because it needs to compare one
segment with the next:

  * inline markup (``<i>``, ``<sc>``, ``<lemma>``) is balanced in every segment, and each
    ``continued_markup`` flag matches the tags it claims were split;
  * segments run forward through the edition (volume, page, line), and the column goes
    back on one page only where the page is divided across its width;
  * a paragraph marked ``run_on`` (v1.3) has a paragraph before it to run on from;
  * an entry of a paragraph's ``apparatus`` (v1.4) finds its ``lemma`` at its place, and a
    node's entry names in ``after`` an id of the document.

Findings are split into two levels:

  * ``ERROR`` — a structural impossibility (unbalanced markup, a flag that
    does not match the text, a location that runs backwards). These fail the
    run.
  * ``WARN``  — something that is *usually* a mistake: a skipped line number
    inside a paragraph. Reported, but never fails the run.

A column that goes back on one page (b, then a again) is neither: the editions have pages
divided across their width, by a question's prologue or a note of the editors set over
both columns, and the columns start again below it. Such places are counted in one line
per document. Where the edition numbers its lines, the lines must still go forward there.

Locations that are not numeric (the scraper's ``"[PAGE]"`` placeholder, roman
numerals) are skipped by the ordering checks.

``join_segments`` is the reference implementation of the joining rule: undo
``continued_markup``, then join the segments with a single space.
``printed_paragraphs`` rebuilds the printed edition's paragraphs: each ``run_on``
paragraph is joined to the one before it, with a single space.
``lemma_at`` is the reference implementation of an apparatus entry's place: the words of
the joined paragraph from ``at``, without the punctuation and markup around them.

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


def iter_paragraphs(nodes):
    """Yield every paragraph, in reading order."""
    for node in nodes or []:
        yield from node.get("paragraphs", []) or []
        yield from iter_paragraphs(node.get("children"))


def printed_paragraphs(doc):
    """The printed edition's paragraphs, as text: each ``run_on`` paragraph is joined to
    the one before it (which may belong to another node) with a single space."""
    out = []
    for para in iter_paragraphs(doc.get("body", [])):
        text = join_segments(para.get("segments", []))
        if para.get("run_on") and out:
            out[-1] += " " + text
        else:
            out.append(text)
    return out


def lemma_at(segments, at, words):
    """The words an apparatus entry stands at: ``words`` words of the joined paragraph
    from word ``at`` (counted from 0, the text split at spaces), without the markup and
    without the punctuation at either end. None if the place is beyond the paragraph."""
    text = join_segments(segments).split(" ")
    if at > len(text) or at + words > len(text):
        return None
    return TAG_RE.sub("", " ".join(text[at:at + words])).strip(" ,.;:?!()")


def iter_nodes(nodes):
    """Yield every node, in reading order."""
    for node in nodes or []:
        yield node
        yield from iter_nodes(node.get("children"))


def check_apparatus(doc):
    """Errors in the apparatus (v1.4): a lemma that is not at its place, an ``after`` that
    names no node or paragraph of the document."""
    errors = []
    nodes = list(iter_nodes(doc.get("body", [])))
    ids = {n.get("node_id") for n in nodes} | {p.get("paragraph_id") for p in iter_paragraphs(doc.get("body", []))}
    for node in nodes:
        for entry in node.get("apparatus", []) or []:
            if "after" in entry and entry["after"] not in ids:
                errors.append(f"{node.get('node_id', '?')}: apparatus names {entry['after']!r}, which is not in the document")
        for para in node.get("paragraphs", []) or []:
            label = para.get("paragraph_id", "?")
            for entry in para.get("apparatus", []) or []:
                if "at" not in entry or "words" not in entry:
                    continue
                try:
                    found = lemma_at(para.get("segments", []), entry["at"], entry["words"])
                except ValueError:
                    continue        # reported with the paragraph's markup
                if found is None:
                    errors.append(f"{label}: apparatus entry at word {entry['at']} is beyond the paragraph")
                elif "lemma" in entry and found != entry["lemma"]:
                    errors.append(f"{label}: apparatus lemma {entry['lemma']!r} is not at word {entry['at']} (found {found!r})")
    return errors


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


def line(seg):
    return (seg.get("edition_location") or {}).get("line")


def describe(seg):
    loc = seg.get("edition_location") or {}
    parts = [f"vol. {loc.get('volume')}", f"p. {loc.get('page')}{loc.get('column', '')}"]
    if "line" in loc:
        parts.append(f"l. {loc['line']}")
    return ", ".join(parts)


def check(doc):
    """Return ``(errors, warnings, divided)``: two lists of human-readable strings, and the
    number of places where the column goes back on one page."""
    errors, warnings = [], []
    last_place, last_where, last_seg = None, None, None
    divided = 0     # a column that goes back on one page: the page is divided across its width

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

        # Location: (volume, page) never runs backwards in reading order. The column may, on
        # one page: a block set over both columns divides the page, and the columns start
        # again below it. If the two segments are of one paragraph and have lines, the
        # lines go on.
        for i, seg in enumerate(segments, 1):
            here = place(seg)
            if here is None:
                continue
            if last_place is not None and here[:2] < last_place[:2]:
                errors.append(f"{label} segment {i} ({describe(seg)}) comes before {last_where}")
            elif last_place is not None and here < last_place:
                la, lb = line(last_seg), line(seg)
                if i > 1 and la is not None and lb is not None and lb <= la:
                    errors.append(f"{label} segment {i} ({describe(seg)}) comes before {last_where}")
                else:
                    divided += 1
            last_place, last_where, last_seg = here, f"{label} ({describe(seg)})", seg

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

    # run_on: the first paragraph of a document has nothing to run on from.
    first = next(iter_paragraphs(doc.get("body", [])), None)
    if first is not None and first.get("run_on"):
        errors.append(f"{first.get('paragraph_id', '?')}: run_on on the document's first paragraph")

    errors.extend(check_apparatus(doc))

    return errors, warnings, divided


def main(argv):
    paths = argv[1:]
    if not paths:
        root = Path(__file__).resolve().parent.parent
        paths = sorted(str(p) for p in (root / "schemas" / "aquinas-opera-omnia").glob("*/examples/*.json"))

    ok = True
    for path in paths:
        errors, warnings, divided = check(load(path))
        print(f"\n{path}")
        if not errors and not warnings:
            print("  [OK] Aquinas integrity clean")
        if divided:
            print(f"  [NOTE]  {divided} place(s) where the column goes back on one page (a page divided across its width)")
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

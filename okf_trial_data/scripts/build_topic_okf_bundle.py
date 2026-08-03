#!/usr/bin/env python3
"""Build a topic-structured OKF v0.2 bundle for one document.

Why this exists
---------------
The first bundle in this repository is *chunk-preserving*: one 500-token
retrieval chunk becomes one concept, and the only links are to the previous and
next chunk. That is a deliberately minimal reading of OKF, and the retrieval
result for it was a null.

It is not, however, what OKF is for. The specification and its launch materials
describe a bundle as a directory of documents where **each document represents
one concept**, organised hierarchically with `index.md` files, and connected by
ordinary Markdown links that express real relationships, so a consumer follows
structure instead of inferring it from embedding similarity.

This producer builds that version for a single document.

How topics are chosen
---------------------
Topics are **not** invented, and no text is rewritten or summarised. The source
PDF carries its own embedded outline - 1,006 entries, six levels deep - which is
the author's own topic hierarchy. Every concept here is one outline entry:

* the concept title is the outline heading, verbatim;
* the concept body is the document text between that heading and the next
  heading, verbatim;
* the hierarchy is the outline's own nesting, mirrored as directories;
* links are parent, children, previous/next sibling, and the cross-references the
  document itself makes ("see Section 8.2").

Headings are located by the exact (page, y) destination recorded for each outline
entry, so section boundaries are precise rather than guessed.

Front matter (the cover, table of contents, and lists of tables and figures)
precedes the first outline entry. It is included as its own top-level topic,
titled from the document's own words, because six benchmark questions have answer
keys on those pages.

Layout
------
Every concept is a named `.md` file, never an `index.md`, because the bundle
loader treats `index.md` and `log.md` as non-concept files. A topic that has
children therefore appears as both a file and a sibling directory::

    concepts/
      index.md                                  bundle index, declares okf_version
      05-risk-methodology-and-assessment.md     the concept
      05-risk-methodology-and-assessment/
        index.md                                directory listing
        5-1-methodology.md
        5-1-methodology/
          5-1-1-overview.md

Usage
-----
    python scripts/build_topic_okf_bundle.py \
        --pdf pge-2026-2028-base-wmp-vol1-r0.pdf \
        --output data/okf_bundles/pge_topics_v0_2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

OKF_VERSION = "0.2"
CORPUS = "PGE"
CORPUS_VERSION = "pge_wmp_r0_20260719"
GENERATED_AT = "2026-08-02T00:00:00Z"
PRODUCER = "process:okf-trial-topic-bundle-v1"
CONCEPT_TYPE = "Document Section"

EVIDENCE_START = "<!-- okf-trial:evidence-start -->"
EVIDENCE_END = "<!-- okf-trial:evidence-end -->"

# Front-matter divisions, matched against the document's own uppercase headings.
FRONT_MATTER_HEADINGS = ("TABLE OF CONTENTS", "LIST OF TABLES", "LIST OF FIGURES")

# "5.2.2.1 Likelihood of Risk Event" -> section number 5.2.2.1
SECTION_NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(.*)$")
# Cross-references the document makes to its own sections.
CROSS_REFERENCE_RE = re.compile(r"\bSections?\s+(\d+(?:\.\d+)+)")


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@dataclass
class Topic:
    """One outline entry and the verbatim text that belongs to it."""

    level: int
    title: str
    page_index: int  # 0-based PDF page
    y: float
    order: int
    section_number: str | None = None
    text: str = ""
    pages: list[int] = field(default_factory=list)  # 1-based PDF pages
    parent: "Topic | None" = None
    children: list["Topic"] = field(default_factory=list)
    slug: str = ""
    relative_path: str = ""  # posix path of the concept file, below the bundle root

    @property
    def concept_id(self) -> str:
        return str(PurePosixPath(self.relative_path).with_suffix(""))

    @property
    def directory(self) -> str:
        """Directory holding this topic's children."""

        return str(PurePosixPath(self.relative_path).with_suffix(""))

    @property
    def title_path(self) -> list[str]:
        chain: list[str] = []
        node: Topic | None = self
        while node is not None:
            chain.append(node.title)
            node = node.parent
        return list(reversed(chain))


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def _slugify(value: str, *, limit: int = 72) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")
    lowered = re.sub(r"-{2,}", "-", lowered)
    return (lowered[:limit].rstrip("-")) or "topic"


def _detect_front_matter(document: Any, first_outline_page: int) -> list[Topic]:
    """Find the document's own front-matter divisions before the outline starts.

    Returns topics for the cover and for each of TABLE OF CONTENTS, LIST OF
    TABLES and LIST OF FIGURES, at their first occurrence.
    """

    cover_title = ""
    first_page_lines = [
        line.strip()
        for line in document[0].get_text().splitlines()
        if line.strip()
    ]
    if first_page_lines:
        cover_title = first_page_lines[0]
    topics = [
        Topic(
            level=2,
            title=cover_title or "Cover",
            page_index=0,
            y=0.0,
            order=0,
        )
    ]
    seen: set[str] = set()
    for page_index in range(first_outline_page):
        for x0, y0, x1, y1, text, *_ in sorted(
            document[page_index].get_text("blocks"), key=lambda b: (round(b[1], 1), b[0])
        ):
            flat = " ".join(text.split()).upper()
            for heading in FRONT_MATTER_HEADINGS:
                if heading in seen or heading not in flat:
                    continue
                seen.add(heading)
                topics.append(
                    Topic(
                        level=2,
                        title=heading.title(),
                        page_index=page_index,
                        y=float(y0),
                        order=0,
                    )
                )
    return topics


def extract_topics(pdf_path: Path) -> tuple[list[Topic], dict[str, Any]]:
    """Read the outline and assign every text block to its owning topic."""

    import fitz

    document = fitz.open(pdf_path)
    outline = document.get_toc(simple=False)
    if not outline:
        raise SystemExit(f"{pdf_path.name} has no embedded outline to derive topics from")

    entries: list[Topic] = []
    first_outline_page = min(int(item[3]["page"]) for item in outline)

    front_matter = _detect_front_matter(document, first_outline_page)
    root_front = Topic(
        level=1,
        title="Front Matter",
        page_index=0,
        y=-1.0,
        order=0,
    )
    entries.append(root_front)
    entries.extend(front_matter)

    for level, title, _page_1based, dest in outline:
        clean_title = " ".join(str(title).split())
        entries.append(
            Topic(
                # Outline levels are used unchanged, so the document's own
                # top-level sections stay top-level. "Front Matter" is their
                # sibling, not their parent.
                level=int(level),
                title=clean_title,
                page_index=int(dest["page"]),
                y=float(dest["to"].y) if dest.get("to") is not None else 0.0,
                order=0,
            )
        )

    # Outline order is authoritative for the hierarchy; position order decides
    # which text belongs to which topic.
    for index, topic in enumerate(entries):
        topic.order = index
        match = SECTION_NUMBER_RE.match(topic.title)
        if match:
            topic.section_number = match.group(1)

    positioned = sorted(entries, key=lambda t: (t.page_index, t.y, t.order))
    boundaries = [(t.page_index, t.y, t) for t in positioned]

    def owner(page_index: int, y: float) -> Topic | None:
        chosen: Topic | None = None
        for b_page, b_y, topic in boundaries:
            if (b_page, b_y) <= (page_index, y):
                chosen = topic
            else:
                break
        return chosen

    buckets: dict[int, list[str]] = {t.order: [] for t in entries}
    bucket_pages: dict[int, set[int]] = {t.order: set() for t in entries}
    for page_index in range(document.page_count):
        blocks = sorted(
            document[page_index].get_text("blocks"), key=lambda b: (round(b[1], 1), b[0])
        )
        for x0, y0, x1, y1, text, *_ in blocks:
            body = text.strip()
            if not body:
                continue
            target = owner(page_index, float(y0))
            if target is None:
                continue
            buckets[target.order].append(body)
            bucket_pages[target.order].add(page_index + 1)

    for topic in entries:
        parts = buckets[topic.order]
        # The heading itself is a text block; drop it so the title is not repeated
        # verbatim at the head of its own body.
        if parts and " ".join(parts[0].split()).casefold() == topic.title.casefold():
            parts = parts[1:]
        topic.text = "\n\n".join(parts).strip()
        topic.pages = sorted(bucket_pages[topic.order])

    # Build the tree from outline levels.
    roots: list[Topic] = []
    stack: list[Topic] = []
    for topic in entries:
        while stack and stack[-1].level >= topic.level:
            stack.pop()
        if stack:
            topic.parent = stack[-1]
            stack[-1].children.append(topic)
        else:
            roots.append(topic)
        stack.append(topic)

    _assign_paths(roots, prefix="concepts")

    stats = {
        "pdf": pdf_path.name,
        "pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        "pdf_pages": document.page_count,
        "outline_entries": len(outline),
        "topics": len(entries),
        "max_depth": max(t.level for t in entries),
        "topics_with_text": sum(1 for t in entries if t.text),
        "empty_topics": sum(1 for t in entries if not t.text),
    }
    document.close()
    return entries, stats


def _assign_paths(topics: Sequence[Topic], *, prefix: str) -> None:
    """Give every topic a unique file path mirroring the outline hierarchy."""

    used: set[str] = set()
    for index, topic in enumerate(topics, start=1):
        # The heading text already begins with its own section number, so slugify
        # only the descriptive remainder to avoid "8-3-8-3-asset-inspections".
        match = SECTION_NUMBER_RE.match(topic.title)
        descriptive = match.group(2) if match else topic.title
        base = _slugify(descriptive)
        if topic.section_number:
            base = f"{_slugify(topic.section_number)}-{base}"
        elif topic.parent is None:
            base = f"{index:02d}-{base}"
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}-{suffix}"
            suffix += 1
        used.add(candidate)
        topic.slug = candidate
        topic.relative_path = f"{prefix}/{candidate}.md"
        if topic.children:
            _assign_paths(topic.children, prefix=f"{prefix}/{candidate}")


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------


def _relative_link(source_path: str, target_path: str) -> str:
    source_dir = PurePosixPath(source_path).parent
    target = PurePosixPath(target_path)
    source_parts = source_dir.parts
    target_parts = target.parts
    common = 0
    while (
        common < len(source_parts)
        and common < len(target_parts) - 1
        and source_parts[common] == target_parts[common]
    ):
        common += 1
    ups = [".."] * (len(source_parts) - common)
    downs = list(target_parts[common:])
    return "/".join(ups + downs) or target.name


def _concept_document(
    topic: Topic, *, stats: dict[str, Any], by_number: dict[str, Topic]
) -> str:
    pdf_sha = stats["pdf_sha256"]
    page_span = (
        f"pages={','.join(str(p) for p in topic.pages)}" if topic.pages else "pages="
    )
    frontmatter: dict[str, Any] = {
        "type": CONCEPT_TYPE,
        "title": topic.title,
        "resource": f"urn:sha256:{pdf_sha}#section={topic.slug}",
        "tags": ["document-section", f"corpus-{CORPUS.lower()}", f"level-{topic.level}"],
        "status": "stable",
        "generated": {"by": PRODUCER, "at": GENERATED_AT},
        "sources": [
            {
                "id": "source-pdf",
                "resource": f"urn:sha256:{pdf_sha}#{page_span}",
                "title": stats["pdf"],
            }
        ],
        "corpus": CORPUS,
        "corpus_version": CORPUS_VERSION,
        # Globally unique and stable. Slugs are only deduplicated within a
        # sibling group, so two topics in different branches can share one.
        "source_chunk_id": f"{CORPUS}-TOPIC-{topic.order:05d}",
        "slug": topic.slug,
        "outline_level": topic.level,
        "outline_order": topic.order,
        "section_number": topic.section_number,
        "section_path": topic.title_path,
        "page_number": topic.pages[0] if topic.pages else None,
        "page_numbers": topic.pages,
        "document_name": stats["pdf"],
        "source_sha256": pdf_sha,
        "content_sha256": hashlib.sha256(topic.text.encode("utf-8")).hexdigest(),
        "child_count": len(topic.children),
    }

    lines = ["---", yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).rstrip(), "---", ""]
    lines += [f"# {topic.title}", "", "## Evidence", "", EVIDENCE_START]
    lines += [topic.text, EVIDENCE_END, ""]

    # Relationships: hierarchy, siblings, and the document's own cross-references.
    relationships: list[str] = []
    if topic.parent is not None:
        relationships.append(
            f"* Parent topic: [{topic.parent.title}]"
            f"({_relative_link(topic.relative_path, topic.parent.relative_path)})"
        )
    siblings = topic.parent.children if topic.parent else []
    if siblings:
        position = siblings.index(topic)
        if position > 0:
            previous = siblings[position - 1]
            relationships.append(
                f"* Previous topic: [{previous.title}]"
                f"({_relative_link(topic.relative_path, previous.relative_path)})"
            )
        if position < len(siblings) - 1:
            following = siblings[position + 1]
            relationships.append(
                f"* Next topic: [{following.title}]"
                f"({_relative_link(topic.relative_path, following.relative_path)})"
            )
    for child in topic.children:
        relationships.append(
            f"* Child topic: [{child.title}]"
            f"({_relative_link(topic.relative_path, child.relative_path)})"
        )
    referenced = []
    for number in dict.fromkeys(CROSS_REFERENCE_RE.findall(topic.text)):
        target = by_number.get(number)
        if target is None or target is topic:
            continue
        referenced.append(
            f"* Referenced section: [{target.title}]"
            f"({_relative_link(topic.relative_path, target.relative_path)})"
        )
    relationships.extend(referenced[:20])
    if relationships:
        lines += ["## Relationships", "", *relationships, ""]

    if topic.pages:
        span = (
            f"page {topic.pages[0]}"
            if len(topic.pages) == 1
            else f"pages {topic.pages[0]}-{topic.pages[-1]}"
        )
    else:
        span = "no extracted pages"
    lines += [
        "## Provenance",
        "",
        f"Extracted from **{stats['pdf']}**, {span}.[^source-pdf]",
        "",
        f"[^source-pdf]: {stats['pdf']}, {span}.",
        "",
    ]
    return "\n".join(lines)


def _directory_index(topic: Topic | None, children: Sequence[Topic], *, is_root: bool) -> str:
    lines: list[str] = []
    if is_root:
        lines += [
            "---",
            yaml.safe_dump(
                {"okf_version": OKF_VERSION, "type": "Index", "title": "PG&E Wildfire Mitigation Plan topics"},
                sort_keys=False,
            ).rstrip(),
            "---",
            "",
            "# PG&E Wildfire Mitigation Plan topics",
            "",
        ]
    else:
        assert topic is not None
        lines += [f"# {topic.title}", ""]
    for child in children:
        target = PurePosixPath(child.relative_path).name
        detail = (
            f" - {len(child.children)} sub-topics"
            if child.children
            else (f" - page {child.pages[0]}" if child.pages else "")
        )
        lines.append(f"* [{child.title}]({target}){detail}")
    lines.append("")
    return "\n".join(lines)


def write_bundle(topics: Sequence[Topic], stats: dict[str, Any], output: Path) -> dict[str, Any]:
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing bundle: {output}")
    by_number = {t.section_number: t for t in topics if t.section_number}

    for topic in topics:
        path = output / topic.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _concept_document(topic, stats=stats, by_number=by_number), encoding="utf-8"
        )

    roots = [t for t in topics if t.parent is None]
    (output / "concepts").mkdir(parents=True, exist_ok=True)
    (output / "concepts/index.md").write_text(
        _directory_index(None, roots, is_root=True), encoding="utf-8"
    )
    for topic in topics:
        if topic.children:
            directory = output / topic.directory
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "index.md").write_text(
                _directory_index(topic, topic.children, is_root=False), encoding="utf-8"
            )

    files = [
        {
            "path": path.relative_to(output).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(output.rglob("*.md"), key=lambda value: value.as_posix())
    ]
    canonical = "".join(f"{item['path']}\0{item['sha256']}\n" for item in files)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    manifest = {
        "okf_version": OKF_VERSION,
        "producer": PRODUCER,
        "generated_at": GENERATED_AT,
        "bundle_kind": "topic_structured",
        "topic_source": "embedded PDF outline (author's own heading hierarchy)",
        "text_policy": "verbatim; no summarisation, rewriting, or invented text",
        "corpus": CORPUS,
        "corpus_version": CORPUS_VERSION,
        "source_pdf": stats["pdf"],
        "source_sha256": stats["pdf_sha256"],
        "concept_count": len(topics),
        "markdown_artifact_count": len(files),
        "max_depth": stats["max_depth"],
        "outline_entries": stats["outline_entries"],
        "bundle_content_sha256": digest,
        "files": files,
    }
    (output / "bundle_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=REPO_ROOT / "pge-2026-2028-base-wmp-vol1-r0.pdf")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "okf_trial_data/data/okf_bundles/pge_topics_v0_2",
    )
    args = parser.parse_args()

    topics, stats = extract_topics(args.pdf)
    manifest = write_bundle(topics, stats, args.output)

    words = [len(t.text.split()) for t in topics if t.text]
    print(f"source            : {stats['pdf']} ({stats['pdf_pages']} pages)")
    print(f"outline entries   : {stats['outline_entries']}")
    print(f"topics (concepts) : {manifest['concept_count']}")
    print(f"markdown files    : {manifest['markdown_artifact_count']}")
    print(f"max depth         : {stats['max_depth']}")
    print(f"topics with text  : {stats['topics_with_text']}  (container-only: {stats['empty_topics']})")
    if words:
        words.sort()
        print(
            f"words per topic   : median {words[len(words)//2]}  "
            f"mean {sum(words)//len(words)}  max {words[-1]}"
        )
    print(f"content digest    : {manifest['bundle_content_sha256']}")
    print(f"written to        : {args.output}")


if __name__ == "__main__":
    main()

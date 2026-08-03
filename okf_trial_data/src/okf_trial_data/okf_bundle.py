"""Deterministic production and consumption of OKF v0.2 evidence bundles.

The producer in this module deliberately has a narrow input surface: a corpus
``manifest.json`` and its extracted ``chunks.jsonl``.  It has no question-set
input and performs no LLM calls.  Consequently, the bundle is fixed before an
evaluation question is observed and cannot leak benchmark questions into the
retrieval representation.

Each source chunk becomes one OKF ``Source Passage`` concept.  Original text,
chunk identifiers, page numbers, document names, corpus versions, and source
hashes are preserved.  Consecutive chunks from the same document are linked so
an OKF consumer can traverse local context without inventing semantic edges.

The implementation targets the exact OKF v0.2 specification revision named by
``OKF_SPEC_COMMIT``.  OKF permits producer-defined frontmatter fields; fields
such as ``source_chunk_id`` and ``page_numbers`` are extensions used to retain
the source evidence's audit trail.
"""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import shutil
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Iterable, Iterator, Mapping, Sequence
from urllib.parse import quote, unquote, urlsplit

import yaml


OKF_VERSION = "0.2"
OKF_SPEC_COMMIT = "3fcbb9f828c2f23d109c855ee403c3a4c81f3a96"
OKF_SPEC_URL = (
    "https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/"
    f"{OKF_SPEC_COMMIT}/okf/SPEC.md"
)
PRODUCER_ID = "process:okf-trial-bundle-v1"
PRODUCER_VERSION = "0.1.0"

_EVIDENCE_START = "<!-- okf-trial:evidence-start -->"
_EVIDENCE_END = "<!-- okf-trial:evidence-end -->"
_FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(?P<yaml>.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL
)
_MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\((?P<target>[^)]+)\)")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FORBIDDEN_EVALUATION_FIELDS = frozenset(
    {
        "question",
        "questions",
        "answer",
        "answers",
        "reference_answer",
        "expected_answer",
        "gold_answer",
        "gold_evidence",
        "qid",
    }
)


class OKFBundleError(ValueError):
    """Base class for bundle input, production, and parsing failures."""


class SourceValidationError(OKFBundleError):
    """The manifest/chunk input is incomplete, inconsistent, or contaminated."""


class BundleFormatError(OKFBundleError):
    """An on-disk bundle cannot be consumed as an OKF v0.2 bundle."""


@dataclass(frozen=True)
class CorpusInput:
    """The two immutable source files from which one corpus is produced."""

    manifest_path: Path
    chunks_path: Path

    @classmethod
    def from_directory(cls, corpus_directory: str | Path) -> "CorpusInput":
        directory = Path(corpus_directory)
        return cls(directory / "manifest.json", directory / "chunks.jsonl")


@dataclass(frozen=True)
class BundleBuildResult:
    """Summary of a completed, atomically installed bundle."""

    bundle_dir: Path
    concept_count: int
    corpus_count: int
    bundle_content_sha256: str
    manifest_path: Path


@dataclass(frozen=True)
class OKFConcept:
    """One parsed OKF concept and the relationships resolved within its bundle."""

    concept_id: str
    relative_path: str
    frontmatter: Mapping[str, Any]
    body: str
    evidence: str
    links: tuple[str, ...]

    @property
    def source_chunk_id(self) -> str:
        return str(self.frontmatter.get("source_chunk_id", self.concept_id))

    @property
    def corpus(self) -> str:
        return str(self.frontmatter.get("corpus", ""))

    @property
    def page_number(self) -> int | None:
        value = self.frontmatter.get("page_number")
        return value if isinstance(value, int) else None


@dataclass(frozen=True)
class _ValidatedCorpus:
    source: CorpusInput
    manifest: Mapping[str, Any]
    chunks: tuple[Mapping[str, Any], ...]
    manifest_sha256: str
    chunks_sha256: str

    @property
    def corpus(self) -> str:
        return str(self.manifest["corpus"])


def discover_corpus_inputs(corpora_root: str | Path) -> list[CorpusInput]:
    """Discover manifest/chunk pairs below ``corpora_root`` in stable order."""

    root = Path(corpora_root)
    inputs = [
        CorpusInput(path, path.with_name("chunks.jsonl"))
        for path in root.glob("*/manifest.json")
        if path.with_name("chunks.jsonl").is_file()
    ]
    return sorted(inputs, key=lambda item: item.manifest_path.as_posix())


def build_okf_bundle(
    sources: Iterable[CorpusInput | str | Path],
    output_dir: str | Path,
    *,
    build_date: str | date,
    generated_at: str | datetime | None = None,
    overwrite: bool = False,
) -> BundleBuildResult:
    """Build an OKF v0.2 bundle deterministically from manifests and chunks.

    Args:
        sources: Corpus directories or explicit :class:`CorpusInput` objects.
            Only ``manifest.json`` and ``chunks.jsonl`` are consumed.
        output_dir: Destination for the completed bundle.
        build_date: ISO date used in the conformant ``log.md``.  It is required
            rather than sampled from the wall clock so repeated builds are
            byte-identical.
        generated_at: Optional ISO-8601 timestamp for ``generated.at``.  If
            supplied, it is normalized to UTC and becomes part of the build
            inputs.  If omitted, the optional OKF ``generated`` family is
            omitted rather than fabricating a timestamp.
        overwrite: Replace an existing destination only when explicitly true.

    Returns:
        Counts, paths, and the SHA-256 digest of every Markdown artifact.

    Raises:
        SourceValidationError: if input provenance is inconsistent, if a chunk
            record contains evaluation-answer fields, or if identifiers collide.
        FileExistsError: if ``output_dir`` exists and ``overwrite`` is false.
    """

    normalized_build_date = _normalise_build_date(build_date)
    normalized_generated_at = _normalise_generated_at(generated_at)
    output = Path(output_dir).expanduser().resolve()
    normalized_sources = tuple(_normalise_source(source) for source in sources)
    if not normalized_sources:
        raise SourceValidationError("at least one corpus source is required")
    _validate_output_target(output, normalized_sources, overwrite=overwrite)

    validated = tuple(_load_and_validate_source(source) for source in normalized_sources)
    validated = tuple(sorted(validated, key=lambda corpus: corpus.corpus.casefold()))

    corpus_names = [corpus.corpus for corpus in validated]
    if len(set(corpus_names)) != len(corpus_names):
        raise SourceValidationError(f"duplicate corpus names: {corpus_names}")

    parent = output.parent
    parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=parent))
    try:
        concept_records = _write_bundle_tree(
            temp_root,
            validated,
            build_date=normalized_build_date,
            generated_at=normalized_generated_at,
        )
        markdown_files = _hash_markdown_files(temp_root)
        content_digest = _digest_file_inventory(markdown_files)
        inventory = {
            "format": "Open Knowledge Format",
            "okf_version": OKF_VERSION,
            "okf_spec_commit": OKF_SPEC_COMMIT,
            "okf_spec_url": OKF_SPEC_URL,
            "producer": {"id": PRODUCER_ID, "version": PRODUCER_VERSION},
            "build_date": normalized_build_date,
            "generated_at": normalized_generated_at,
            "corpus_count": len(validated),
            "concept_count": len(concept_records),
            "bundle_content_sha256": content_digest,
            "sources": [
                {
                    "corpus": item.corpus,
                    "corpus_version": item.manifest["corpus_version"],
                    "source_pdf": item.manifest["source_pdf"],
                    "source_sha256": item.manifest["source_sha256"],
                    "manifest_filename": item.source.manifest_path.name,
                    "manifest_sha256": item.manifest_sha256,
                    "chunks_filename": item.source.chunks_path.name,
                    "chunks_sha256": item.chunks_sha256,
                    "concept_count": len(item.chunks),
                    "source_manifest": item.manifest,
                }
                for item in validated
            ],
            "files": markdown_files,
        }
        _write_json(temp_root / "bundle_manifest.json", inventory)

        # Parse what was written before making it visible at the requested path.
        parsed = OKFBundle.load(temp_root)
        if len(parsed) != len(concept_records):
            raise BundleFormatError(
                f"wrote {len(concept_records)} concepts but parsed {len(parsed)}"
            )
        parsed.verify_integrity()

        if output.exists():
            if not overwrite:
                raise FileExistsError(
                    f"bundle destination already exists: {output}; pass overwrite=True"
                )
            if output.is_dir():
                shutil.rmtree(output)
            else:
                output.unlink()
        os.replace(temp_root, output)
    except Exception:
        if temp_root.exists():
            shutil.rmtree(temp_root)
        raise

    return BundleBuildResult(
        bundle_dir=output,
        concept_count=len(concept_records),
        corpus_count=len(validated),
        bundle_content_sha256=content_digest,
        manifest_path=output / "bundle_manifest.json",
    )


class OKFBundle:
    """Read-only in-memory view of an OKF bundle and its concept graph."""

    def __init__(
        self,
        root: Path,
        concepts: Mapping[str, OKFConcept],
        incoming_links: Mapping[str, tuple[str, ...]],
    ) -> None:
        self.root = root
        self._concepts = MappingProxyType(dict(concepts))
        self._incoming_links = MappingProxyType(dict(incoming_links))
        by_source: dict[tuple[str, str], str] = {}
        for concept in concepts.values():
            key = (concept.corpus, concept.source_chunk_id)
            if key in by_source:
                raise BundleFormatError(
                    "duplicate (corpus, source_chunk_id) mapping in bundle: "
                    f"{key!r}"
                )
            by_source[key] = concept.concept_id
        self._by_source_chunk = MappingProxyType(by_source)

    @classmethod
    def load(cls, bundle_dir: str | Path) -> "OKFBundle":
        """Parse all non-reserved Markdown concepts and resolve local links.

        Broken links are ignored, as required by OKF v0.2 conformance.  Invalid
        concept frontmatter and missing ``type`` values fail closed.
        """

        root = Path(bundle_dir).expanduser().resolve()
        if not root.is_dir():
            raise BundleFormatError(f"bundle directory does not exist: {root}")
        _validate_root_version(root)

        raw: dict[str, tuple[str, Mapping[str, Any], str, str]] = {}
        for path in sorted(root.rglob("*.md"), key=lambda value: value.as_posix()):
            if path.name in {"index.md", "log.md"}:
                continue
            relative_path = path.relative_to(root).as_posix()
            concept_id = str(PurePosixPath(relative_path).with_suffix(""))
            text = path.read_text(encoding="utf-8")
            frontmatter, body = parse_concept_document(text, source=relative_path)
            evidence = _extract_evidence(body)
            raw[concept_id] = (relative_path, frontmatter, body, evidence)

        concepts: dict[str, OKFConcept] = {}
        incoming: dict[str, set[str]] = {concept_id: set() for concept_id in raw}
        for concept_id, (relative_path, frontmatter, body, evidence) in raw.items():
            resolved: list[str] = []
            for target in _iter_markdown_targets(body):
                linked_id = _resolve_concept_link(relative_path, target)
                if linked_id is None or linked_id not in raw or linked_id == concept_id:
                    continue
                if linked_id not in resolved:
                    resolved.append(linked_id)
                    incoming[linked_id].add(concept_id)
            concepts[concept_id] = OKFConcept(
                concept_id=concept_id,
                relative_path=relative_path,
                frontmatter=_freeze_mapping(frontmatter),
                body=body,
                evidence=evidence,
                links=tuple(resolved),
            )
        frozen_incoming = {
            concept_id: tuple(sorted(sources)) for concept_id, sources in incoming.items()
        }
        return cls(root, concepts, frozen_incoming)

    def __len__(self) -> int:
        return len(self._concepts)

    def __iter__(self) -> Iterator[OKFConcept]:
        for concept_id in sorted(self._concepts):
            yield self._concepts[concept_id]

    @property
    def concepts(self) -> Mapping[str, OKFConcept]:
        return self._concepts

    def get(self, concept_id: str) -> OKFConcept | None:
        return self._concepts.get(concept_id)

    def concept_for_source_chunk(self, corpus: str, chunk_id: str) -> OKFConcept | None:
        concept_id = self._by_source_chunk.get((str(corpus), str(chunk_id)))
        return self._concepts.get(concept_id) if concept_id else None

    def neighbors(self, concept_id: str, *, bidirectional: bool = True) -> tuple[str, ...]:
        concept = self._concepts.get(concept_id)
        if concept is None:
            return ()
        result = set(concept.links)
        if bidirectional:
            result.update(self._incoming_links.get(concept_id, ()))
        return tuple(sorted(result))

    def verify_integrity(self) -> None:
        """Verify every recorded Markdown hash and the aggregate bundle digest."""

        manifest_path = self.root / "bundle_manifest.json"
        if not manifest_path.is_file():
            raise BundleFormatError("bundle_manifest.json is missing")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BundleFormatError(f"cannot parse bundle_manifest.json: {exc}") from exc
        expected_files = manifest.get("files")
        if not isinstance(expected_files, list):
            raise BundleFormatError("bundle manifest 'files' must be a list")
        actual_files = _hash_markdown_files(self.root)
        if actual_files != expected_files:
            raise BundleFormatError("bundle Markdown inventory does not match recorded hashes")
        actual_digest = _digest_file_inventory(actual_files)
        if actual_digest != manifest.get("bundle_content_sha256"):
            raise BundleFormatError("bundle content digest does not match recorded digest")


def parse_concept_document(
    text: str, *, source: str = "<memory>"
) -> tuple[dict[str, Any], str]:
    """Parse and minimally validate an OKF v0.2 concept document."""

    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise BundleFormatError(f"{source}: missing parseable YAML frontmatter")
    try:
        frontmatter = yaml.safe_load(match.group("yaml"))
    except yaml.YAMLError as exc:
        raise BundleFormatError(f"{source}: invalid YAML frontmatter: {exc}") from exc
    if not isinstance(frontmatter, dict):
        raise BundleFormatError(f"{source}: frontmatter must be a mapping")
    concept_type = frontmatter.get("type")
    if not isinstance(concept_type, str) or not concept_type.strip():
        raise BundleFormatError(f"{source}: frontmatter requires a non-empty 'type'")
    return frontmatter, text[match.end() :]


def _normalise_source(source: CorpusInput | str | Path) -> CorpusInput:
    if isinstance(source, CorpusInput):
        return CorpusInput(
            Path(source.manifest_path).expanduser().resolve(),
            Path(source.chunks_path).expanduser().resolve(),
        )
    return CorpusInput.from_directory(Path(source).expanduser().resolve())


def _validate_output_target(
    output: Path, sources: Sequence[CorpusInput], *, overwrite: bool
) -> None:
    """Refuse broad or source-overlapping replacement targets.

    ``overwrite=True`` is intentionally limited to bundles previously produced
    by this package (or an empty destination directory).  This makes repeated
    experiment builds convenient without turning a typo into recursive removal
    of a repository, home directory, or input corpus.
    """

    filesystem_root = Path(output.anchor).resolve()
    if output in {filesystem_root, Path.home().resolve()}:
        raise SourceValidationError(f"unsafe bundle output target: {output}")
    for source in sources:
        for input_path in (source.manifest_path, source.chunks_path):
            if output == input_path or output in input_path.parents:
                raise SourceValidationError(
                    f"bundle output must not contain or replace source input: {input_path}"
                )
    if not output.exists() or not overwrite:
        return
    if not output.is_dir():
        raise SourceValidationError(
            "overwrite is allowed only for a directory created by okf-trial-data"
        )
    entries = list(output.iterdir())
    if not entries:
        return
    marker = output / "bundle_manifest.json"
    try:
        manifest = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceValidationError(
            "refusing to overwrite a non-empty directory without a valid "
            "okf-trial-data bundle manifest"
        ) from exc
    producer = manifest.get("producer")
    if not isinstance(producer, dict) or producer.get("id") != PRODUCER_ID:
        raise SourceValidationError(
            "refusing to overwrite a directory not produced by okf-trial-data"
        )


def _load_and_validate_source(source: CorpusInput) -> _ValidatedCorpus:
    if not source.manifest_path.is_file():
        raise SourceValidationError(f"manifest not found: {source.manifest_path}")
    if not source.chunks_path.is_file():
        raise SourceValidationError(f"chunks JSONL not found: {source.chunks_path}")
    try:
        manifest = json.loads(source.manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceValidationError(f"invalid manifest JSON: {source.manifest_path}") from exc
    if not isinstance(manifest, dict):
        raise SourceValidationError(f"manifest must contain one JSON object: {source.manifest_path}")
    leaked_manifest_fields = sorted(_FORBIDDEN_EVALUATION_FIELDS.intersection(manifest))
    if leaked_manifest_fields:
        raise SourceValidationError(
            f"manifest contains forbidden evaluation fields: {leaked_manifest_fields}"
        )
    required = ("corpus", "corpus_version", "source_pdf", "source_sha256", "n_chunks")
    missing = [key for key in required if key not in manifest]
    if missing:
        raise SourceValidationError(f"manifest missing required fields: {missing}")
    for key in ("corpus", "corpus_version", "source_pdf"):
        if not isinstance(manifest[key], str) or not manifest[key].strip():
            raise SourceValidationError(f"manifest field {key!r} must be a non-empty string")
    if not isinstance(manifest["source_sha256"], str) or not _SHA256_RE.fullmatch(
        manifest["source_sha256"]
    ):
        raise SourceValidationError("manifest source_sha256 must be 64 hexadecimal characters")
    if not isinstance(manifest["n_chunks"], int) or manifest["n_chunks"] < 0:
        raise SourceValidationError("manifest n_chunks must be a non-negative integer")

    chunks: list[Mapping[str, Any]] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(
        source.chunks_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SourceValidationError(
                f"{source.chunks_path}:{line_number}: invalid JSON"
            ) from exc
        if not isinstance(record, dict):
            raise SourceValidationError(
                f"{source.chunks_path}:{line_number}: chunk must be an object"
            )
        leaked = sorted(_FORBIDDEN_EVALUATION_FIELDS.intersection(record))
        if leaked:
            raise SourceValidationError(
                f"{source.chunks_path}:{line_number}: evaluation fields are forbidden: {leaked}"
            )
        for key in ("chunk_id", "corpus", "text"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise SourceValidationError(
                    f"{source.chunks_path}:{line_number}: {key!r} must be a non-empty string"
                )
        if record["corpus"] != manifest["corpus"]:
            raise SourceValidationError(
                f"{source.chunks_path}:{line_number}: corpus {record['corpus']!r} "
                f"does not match manifest corpus {manifest['corpus']!r}"
            )
        if record["chunk_id"] in seen_ids:
            raise SourceValidationError(f"duplicate chunk_id: {record['chunk_id']}")
        seen_ids.add(record["chunk_id"])
        _validate_page_data(record, source.chunks_path, line_number)
        if _EVIDENCE_START in record["text"] or _EVIDENCE_END in record["text"]:
            raise SourceValidationError(
                f"{source.chunks_path}:{line_number}: source text contains a reserved evidence marker"
            )
        chunks.append(record)

    if len(chunks) != manifest["n_chunks"]:
        raise SourceValidationError(
            f"manifest records n_chunks={manifest['n_chunks']}, but chunks JSONL contains "
            f"{len(chunks)} records"
        )
    return _ValidatedCorpus(
        source=source,
        manifest=manifest,
        chunks=tuple(chunks),
        manifest_sha256=_sha256_file(source.manifest_path),
        chunks_sha256=_sha256_file(source.chunks_path),
    )


def _validate_page_data(record: Mapping[str, Any], path: Path, line_number: int) -> None:
    page = record.get("page_number")
    if page is not None and (not isinstance(page, int) or isinstance(page, bool) or page < 1):
        raise SourceValidationError(
            f"{path}:{line_number}: page_number must be a positive integer or null"
        )
    metadata = record.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise SourceValidationError(f"{path}:{line_number}: metadata must be an object")
    pages = metadata.get("pages", [])
    if pages is None:
        pages = []
    if not isinstance(pages, list) or any(
        not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in pages
    ):
        raise SourceValidationError(
            f"{path}:{line_number}: metadata.pages must be a list of positive integers"
        )


def _write_bundle_tree(
    root: Path,
    corpora: Sequence[_ValidatedCorpus],
    *,
    build_date: str,
    generated_at: str | None,
) -> list[dict[str, Any]]:
    concepts_root = root / "concepts"
    concepts_root.mkdir(parents=True)
    all_records: list[dict[str, Any]] = []
    corpus_index_entries: list[str] = []

    used_corpus_slugs: set[str] = set()
    for corpus_data in corpora:
        corpus = corpus_data.corpus
        corpus_slug = _slug(corpus)
        if corpus_slug in used_corpus_slugs:
            raise SourceValidationError(f"corpus directory slug collision: {corpus!r}")
        used_corpus_slugs.add(corpus_slug)
        corpus_dir = concepts_root / corpus_slug
        corpus_dir.mkdir()
        path_by_index = _concept_paths(corpus_data, corpus_slug)

        index_lines = [f"# {corpus} source passages", ""]
        chunks = corpus_data.chunks
        for index, chunk in enumerate(chunks):
            relative_path = path_by_index[index]
            concept_path = root / relative_path
            pages = _page_numbers(chunk)
            document_name = str(
                chunk.get("document_name") or corpus_data.manifest["source_pdf"]
            )
            section = chunk.get("section")
            links: list[tuple[str, str]] = []
            if index > 0 and _same_document(chunks[index - 1], chunk, corpus_data.manifest):
                links.append(("Previous passage", "/" + path_by_index[index - 1]))
            if index + 1 < len(chunks) and _same_document(
                chunk, chunks[index + 1], corpus_data.manifest
            ):
                links.append(("Next passage", "/" + path_by_index[index + 1]))

            description = _passage_description(chunk["chunk_id"], document_name, pages)
            frontmatter: dict[str, Any] = {
                "type": "Source Passage",
                "title": _passage_title(chunk["chunk_id"], section, pages),
                "description": description,
                "resource": _chunk_resource(
                    corpus_data.manifest["source_sha256"], chunk["chunk_id"]
                ),
                "tags": ["source-passage", f"corpus-{corpus_slug}"],
                "status": "stable",
            }
            if generated_at is not None:
                frontmatter["generated"] = {"by": PRODUCER_ID, "at": generated_at}
            source: dict[str, Any] = {
                "id": "source-pdf",
                "resource": _source_resource(corpus_data.manifest["source_sha256"], pages),
                "title": document_name,
            }
            frontmatter["sources"] = [source]
            frontmatter.update(
                {
                    "corpus": corpus,
                    "corpus_version": corpus_data.manifest["corpus_version"],
                    "source_chunk_id": chunk["chunk_id"],
                    "source_order": index,
                    "page_number": chunk.get("page_number"),
                    "page_numbers": pages,
                    "section": section,
                    "document_name": document_name,
                    "source_sha256": corpus_data.manifest["source_sha256"].lower(),
                    "content_sha256": _sha256_text(chunk["text"]),
                    "source_metadata": chunk.get("metadata") or {},
                }
            )
            body = _concept_body(chunk["text"], document_name, pages, links)
            _write_concept(concept_path, frontmatter, body)
            index_lines.append(
                f"* [{chunk['chunk_id']}]({Path(relative_path).name}) - {description}"
            )
            all_records.append(
                {
                    "concept_id": str(PurePosixPath(relative_path).with_suffix("")),
                    "path": relative_path,
                    "corpus": corpus,
                    "source_chunk_id": chunk["chunk_id"],
                    "source_order": index,
                    "pages": pages,
                }
            )
        (corpus_dir / "index.md").write_text(
            "\n".join(index_lines).rstrip() + "\n", encoding="utf-8", newline="\n"
        )
        corpus_index_entries.append(
            f"* [{corpus}]({corpus_slug}/) - {len(chunks)} source-passage concepts"
        )

    concepts_index = "\n".join(["# Corpora", "", *corpus_index_entries]).rstrip() + "\n"
    (concepts_root / "index.md").write_text(
        concepts_index, encoding="utf-8", newline="\n"
    )
    root_index = "\n".join(
        [
            "---",
            f'okf_version: "{OKF_VERSION}"',
            "---",
            "# OKF Trial Evidence Bundle",
            "",
            "This question-independent bundle contains source passages for a controlled RAG benchmark.",
            "",
            "## Contents",
            "",
            "* [Corpus concepts](concepts/) - Source passages grouped by corpus",
            "",
            "## Specification pin",
            "",
            f"Produced for [OKF v{OKF_VERSION} at `{OKF_SPEC_COMMIT}`]({OKF_SPEC_URL}).",
        ]
    )
    (root / "index.md").write_text(root_index.rstrip() + "\n", encoding="utf-8", newline="\n")
    log_text = "\n".join(
        [
            "# Bundle Update Log",
            "",
            f"## {build_date}",
            f"* **Generation**: Created {len(all_records)} source-passage concepts from "
            f"{len(corpora)} immutable corpus snapshots.",
            f"* **Specification**: Targeted OKF v{OKF_VERSION} at commit `{OKF_SPEC_COMMIT}`.",
        ]
    )
    (root / "log.md").write_text(log_text.rstrip() + "\n", encoding="utf-8", newline="\n")
    return all_records


def _concept_paths(corpus_data: _ValidatedCorpus, corpus_slug: str) -> list[str]:
    paths: list[str] = []
    used: set[str] = set()
    for chunk in corpus_data.chunks:
        filename = _slug(chunk["chunk_id"]) + ".md"
        relative = f"concepts/{corpus_slug}/{filename}"
        if relative in used:
            raise SourceValidationError(
                f"chunk identifiers collide after path normalization: {chunk['chunk_id']!r}"
            )
        used.add(relative)
        paths.append(relative)
    return paths


def _same_document(
    left: Mapping[str, Any], right: Mapping[str, Any], manifest: Mapping[str, Any]
) -> bool:
    default = manifest["source_pdf"]
    return (left.get("document_name") or default) == (right.get("document_name") or default)


def _write_concept(path: Path, frontmatter: Mapping[str, Any], body: str) -> None:
    dumped = yaml.safe_dump(
        dict(frontmatter),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=4096,
    ).rstrip()
    text = f"---\n{dumped}\n---\n{body.rstrip()}\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def _concept_body(
    text: str,
    document_name: str,
    pages: Sequence[int],
    links: Sequence[tuple[str, str]],
) -> str:
    page_label = _format_pages(pages)
    # Joining places exactly one framing newline on either side of ``text``.
    # The consumer removes exactly those two bytes, retaining any newlines that
    # were already present in the source chunk.
    lines = ["# Evidence", "", _EVIDENCE_START, text, _EVIDENCE_END]
    if links:
        lines.extend(["", "## Relationships", ""])
        lines.extend(f"* {label}: [source passage]({target})" for label, target in links)
    lines.extend(
        [
            "",
            "## Provenance",
            "",
            f"Extracted from **{document_name}**, {page_label}.[^source-pdf]",
            "",
            f"[^source-pdf]: {document_name}, {page_label}.",
        ]
    )
    return "\n".join(lines)


def _passage_title(chunk_id: str, section: Any, pages: Sequence[int]) -> str:
    if isinstance(section, str) and section.strip():
        return f"{chunk_id} — {section.strip()}"
    return f"{chunk_id} — {_format_pages(pages).title()}"


def _passage_description(chunk_id: str, document_name: str, pages: Sequence[int]) -> str:
    return f"Source chunk {chunk_id} from {document_name}, {_format_pages(pages)}."


def _format_pages(pages: Sequence[int]) -> str:
    if not pages:
        return "page not recorded"
    if len(pages) == 1:
        return f"page {pages[0]}"
    return "pages " + ", ".join(str(page) for page in pages)


def _page_numbers(chunk: Mapping[str, Any]) -> list[int]:
    pages: list[int] = []
    metadata = chunk.get("metadata") or {}
    for value in metadata.get("pages") or []:
        if value not in pages:
            pages.append(value)
    primary = chunk.get("page_number")
    if primary is not None and primary not in pages:
        pages.insert(0, primary)
    return pages


def _chunk_resource(source_sha256: str, chunk_id: str) -> str:
    return f"urn:sha256:{source_sha256.lower()}#chunk={quote(str(chunk_id), safe='-._~')}"


def _source_resource(source_sha256: str, pages: Sequence[int]) -> str:
    fragment = "pages=" + ",".join(str(page) for page in pages) if pages else "document"
    return f"urn:sha256:{source_sha256.lower()}#{fragment}"


def _extract_evidence(body: str) -> str:
    start = body.find(_EVIDENCE_START)
    end = body.find(_EVIDENCE_END, start + len(_EVIDENCE_START)) if start >= 0 else -1
    if start < 0 or end < 0:
        return body.strip()
    evidence = body[start + len(_EVIDENCE_START) : end]
    if evidence.startswith("\r\n"):
        evidence = evidence[2:]
    elif evidence.startswith("\n"):
        evidence = evidence[1:]
    if evidence.endswith("\r\n"):
        evidence = evidence[:-2]
    elif evidence.endswith("\n"):
        evidence = evidence[:-1]
    return evidence


def _iter_markdown_targets(body: str) -> Iterator[str]:
    for match in _MARKDOWN_LINK_RE.finditer(body):
        target = match.group("target").strip()
        # Markdown permits an optional title after a whitespace separator.  The
        # producer emits no titles, but accepting them keeps this a useful OKF
        # consumer for hand-authored bundles.
        if target.startswith("<") and ">" in target:
            target = target[1 : target.index(">")]
        elif " " in target:
            target = target.split(" ", 1)[0]
        yield target


def _resolve_concept_link(relative_path: str, target: str) -> str | None:
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    path = unquote(parsed.path)
    if path.startswith("/"):
        normalized = posixpath.normpath(path.lstrip("/"))
    else:
        normalized = posixpath.normpath(
            posixpath.join(posixpath.dirname(relative_path), path)
        )
    if normalized.startswith("../") or normalized in {".", ".."}:
        return None
    if normalized.endswith("/"):
        return None
    candidate = PurePosixPath(normalized)
    if candidate.name in {"index.md", "log.md"} or candidate.suffix.lower() != ".md":
        return None
    return str(candidate.with_suffix(""))


def _validate_root_version(root: Path) -> None:
    index = root / "index.md"
    if not index.is_file():
        return
    text = index.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return
    try:
        data = yaml.safe_load(match.group("yaml"))
    except yaml.YAMLError as exc:
        raise BundleFormatError(f"index.md: invalid YAML frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise BundleFormatError("index.md frontmatter must be a mapping")
    version = str(data.get("okf_version", ""))
    if version and version != OKF_VERSION:
        raise BundleFormatError(
            f"bundle declares OKF {version!r}; this consumer is pinned to {OKF_VERSION!r}"
        )


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    # A shallow proxy prevents accidental replacement of provenance fields.  A
    # deep copy through JSON also removes PyYAML-specific mapping subclasses.
    copied = json.loads(json.dumps(value, ensure_ascii=False, default=str))
    return MappingProxyType(copied)


def _normalise_build_date(value: str | date) -> str:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str) or not _ISO_DATE_RE.fullmatch(value):
        raise SourceValidationError("build_date must use ISO YYYY-MM-DD form")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise SourceValidationError("build_date is not a valid calendar date") from exc
    return value


def _normalise_generated_at(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        candidate = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError as exc:
            raise SourceValidationError("generated_at must be an ISO-8601 datetime") from exc
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise SourceValidationError("generated_at must be a datetime, ISO string, or null")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SourceValidationError("generated_at must include a timezone")
    utc = parsed.astimezone(timezone.utc)
    return utc.isoformat(timespec="seconds").replace("+00:00", "Z")


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.casefold()).strip("-")
    if slug:
        return slug
    return "id-" + _sha256_text(str(value))[:12]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _hash_markdown_files(root: Path) -> list[dict[str, str]]:
    return [
        {"path": path.relative_to(root).as_posix(), "sha256": _sha256_file(path)}
        for path in sorted(root.rglob("*.md"), key=lambda value: value.as_posix())
    ]


def _digest_file_inventory(files: Sequence[Mapping[str, str]]) -> str:
    canonical = "".join(f"{item['path']}\0{item['sha256']}\n" for item in files)
    return _sha256_text(canonical)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

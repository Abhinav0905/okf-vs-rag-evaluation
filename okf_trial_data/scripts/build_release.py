#!/usr/bin/env python3
"""Validate, inventory, and archive the public OKF trial artifact."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "okf_trial_data"
DEFAULT_MANIFEST = PACKAGE_ROOT / "release_manifest.json"
DEFAULT_ARCHIVE = PACKAGE_ROOT / "output/release/okf_trial_artifact.zip"
DEFAULT_SOURCE_DATE_EPOCH = 1_785_628_800  # 2026-08-02T00:00:00Z

INCLUDE_FILES = (
    "README.md",
    "RELEASE_CHECKLIST.md",
    "environment_manifest.json",
    "pyproject.toml",
)
INCLUDE_DIRECTORIES = (
    "config",
    "data/okf_bundles",
    "paper",
    "protocol",
    "scripts",
    "src",
    "tests",
    "results/retrieval",
    "results/full",
    "output/pdf",
)
OPTIONAL_FILES = (
    "CITATION.cff",
    "DATA_LICENSE.md",
    "LICENSE",
    "data/benchmark_questions.json",
    "data/gold_audit.jsonl",
    "data/gold_audit_summary.json",
    "results/build_metrics.json",
)
EXCLUDED_PARTS = {
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    ".DS_Store",
}

SECRET_PATTERNS = {
    "aws_access_key_id": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "aws_secret_assignment": re.compile(rb"AWS_SECRET_ACCESS_KEY\s*=", re.IGNORECASE),
    "aws_session_assignment": re.compile(rb"AWS_SESSION_TOKEN\s*=", re.IGNORECASE),
    "bedrock_api_assignment": re.compile(
        rb"(?:AWS_BEARER_TOKEN_BEDROCK|BEDROCK[-_]API[-_]KEY)\s*=", re.IGNORECASE
    ),
    "openai_key_assignment": re.compile(rb"OPENAI_API_KEY\s*=", re.IGNORECASE),
    "github_token": re.compile(rb"\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "aws_arn": re.compile(rb"\barn:aws(?:-[a-z]+)?:[A-Za-z0-9_./:=+@-]+"),
    "absolute_macos_home": re.compile(rb"/Users/" + rb"[^/\s]+/"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _included_files(*, excluded_paths: set[Path] | None = None) -> list[Path]:
    excluded = {path.resolve() for path in (excluded_paths or set())}
    paths: set[Path] = set()
    for relative in INCLUDE_FILES:
        path = PACKAGE_ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        paths.add(path)
    for relative in OPTIONAL_FILES:
        path = PACKAGE_ROOT / relative
        if path.is_file():
            paths.add(path)
    for relative in INCLUDE_DIRECTORIES:
        directory = PACKAGE_ROOT / relative
        if not directory.is_dir():
            raise FileNotFoundError(directory)
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise RuntimeError(f"release tree contains a symlink: {path}")
            if (
                not path.is_file()
                or EXCLUDED_PARTS.intersection(path.parts)
                or any(part.endswith(".egg-info") for part in path.parts)
            ):
                continue
            paths.add(path)
    paths = {path for path in paths if path.resolve() not in excluded}
    return sorted(paths, key=lambda path: path.relative_to(PACKAGE_ROOT).as_posix())


def _validate_completion() -> dict[str, int]:
    paths = {
        "generation_records": PACKAGE_ROOT / "results/full/generation_records.jsonl",
        "answer_scores": PACKAGE_ROOT / "results/full/answer_scores.jsonl",
        "judge_trial_records": PACKAGE_ROOT / "results/full/judge_trial_records.jsonl",
    }
    counts = {
        name: sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line)
        for name, path in paths.items()
    }
    run_manifest = json.loads(
        (PACKAGE_ROOT / "results/full/run_manifest.json").read_text(encoding="utf-8")
    )
    judge_manifest = json.loads(
        (PACKAGE_ROOT / "results/full/judge_manifest.json").read_text(encoding="utf-8")
    )
    answer_cells = int(run_manifest["expected_records"])
    expected = {
        "generation_records": answer_cells,
        "answer_scores": answer_cells,
        "judge_trial_records": int(judge_manifest["expected_trial_records"]),
    }
    if counts != expected:
        raise RuntimeError(f"release completion gate failed: {counts} != {expected}")
    if int(judge_manifest["answer_count"]) != answer_cells:
        raise RuntimeError("judge manifest answer count differs from the run manifest")
    if int(judge_manifest["trials_per_answer"]) * answer_cells != expected["judge_trial_records"]:
        raise RuntimeError("judge manifest trial product is inconsistent")
    analysis = json.loads(
        (PACKAGE_ROOT / "results/full/analysis/analysis_summary.json").read_text(
            encoding="utf-8"
        )
    )
    completion = analysis.get("completion", {})
    if not completion.get("complete"):
        raise RuntimeError("analysis completion flag is false")
    for name, count in counts.items():
        if int(completion.get(name, -1)) != count:
            raise RuntimeError(
                f"analysis completion count for {name} does not match records"
            )
    design = analysis.get("study_design", {})
    benchmark_path = PACKAGE_ROOT / "data/benchmark_questions.json"
    if design.get("benchmark_id") != run_manifest.get("benchmark_id"):
        raise RuntimeError("analysis and run manifest benchmark IDs differ")
    if design.get("benchmark_sha256") != _sha256(benchmark_path):
        raise RuntimeError("analysis benchmark hash differs from the release benchmark")
    if design.get("superseded_partial_run_included") is not False:
        raise RuntimeError("analysis does not explicitly exclude the superseded partial run")
    pdf = PACKAGE_ROOT / "output/pdf/okf_rag_preprint.pdf"
    if not pdf.is_file() or pdf.stat().st_size < 10_000:
        raise RuntimeError("final manuscript PDF is absent or unexpectedly small")
    return counts


def _canonical_json_bytes(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")


def _public_payloads(files: list[Path]) -> tuple[dict[Path, bytes], list[dict[str, str]]]:
    """Create release bytes without publishing even hashed cloud identities."""

    payloads = {path: path.read_bytes() for path in files}
    transformations: list[dict[str, str]] = []
    run_manifest = PACKAGE_ROOT / "results/full/run_manifest.json"
    if run_manifest in payloads:
        run_data = json.loads(payloads[run_manifest].decode("utf-8"))
        if run_data.pop("aws_identity", None) is not None:
            payloads[run_manifest] = _canonical_json_bytes(run_data)
            transformations.append(
                {
                    "path": run_manifest.relative_to(PACKAGE_ROOT).as_posix(),
                    "operation": "removed aws_identity from public copy",
                }
            )
    judge_manifest = PACKAGE_ROOT / "results/full/judge_manifest.json"
    if judge_manifest in payloads:
        judge_data = json.loads(payloads[judge_manifest].decode("utf-8"))
        changed = judge_data.pop("aws_identity", None) is not None
        if run_manifest in payloads:
            public_run_digest = hashlib.sha256(payloads[run_manifest]).hexdigest()
            if judge_data.get("generation_manifest_sha256") != public_run_digest:
                judge_data["generation_manifest_sha256"] = public_run_digest
                changed = True
        if changed:
            payloads[judge_manifest] = _canonical_json_bytes(judge_data)
            transformations.append(
                {
                    "path": judge_manifest.relative_to(PACKAGE_ROOT).as_posix(),
                    "operation": (
                        "removed aws_identity and updated the public generation-manifest hash"
                    ),
                }
            )
    return payloads, transformations


def _secret_scan(payloads: dict[Path, bytes]) -> None:
    findings: list[str] = []
    forbidden_suffixes = {".pem", ".key", ".p12", ".pfx"}
    for path, data in payloads.items():
        relative = path.relative_to(PACKAGE_ROOT).as_posix()
        if path.name.casefold().startswith(".env") or path.suffix.lower() in forbidden_suffixes:
            findings.append(f"forbidden filename: {relative}")
            continue
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(data):
                findings.append(f"{name}: {relative}")
    if findings:
        raise RuntimeError("release secret scan failed: " + "; ".join(findings))


def _inventory(payloads: dict[Path, bytes]) -> list[dict[str, object]]:
    return [
        {
            "path": path.relative_to(PACKAGE_ROOT).as_posix(),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        for path, data in payloads.items()
    ]


def _inventory_digest(inventory: list[dict[str, object]]) -> str:
    canonical = json.dumps(inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_reproducible_zip(
    archive_path: Path,
    payloads: dict[Path, bytes],
    manifest_bytes: bytes,
    *,
    source_date_epoch: int,
) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromtimestamp(source_date_epoch, timezone.utc)
    if stamp.year < 1980:
        raise ValueError("source-date-epoch must be representable by the ZIP format")
    zip_stamp = (stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute, stamp.second)
    archive_payloads = dict(payloads)
    archive_payloads[PACKAGE_ROOT / "release_manifest.json"] = manifest_bytes
    temporary = archive_path.with_suffix(archive_path.suffix + ".tmp")
    with zipfile.ZipFile(
        temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path, data in sorted(
            archive_payloads.items(),
            key=lambda item: item[0].relative_to(PACKAGE_ROOT).as_posix(),
        ):
            relative = Path("okf_trial_data") / path.relative_to(PACKAGE_ROOT)
            info = zipfile.ZipInfo(relative.as_posix(), date_time=zip_stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    temporary.replace(archive_path)


def _validate_final_metadata(payloads: dict[Path, bytes]) -> None:
    required = [
        PACKAGE_ROOT / "LICENSE",
        PACKAGE_ROOT / "DATA_LICENSE.md",
        PACKAGE_ROOT / "CITATION.cff",
        PACKAGE_ROOT / "paper/manuscript.md",
        PACKAGE_ROOT / "paper/manuscript.tex",
    ]
    missing = [path.relative_to(PACKAGE_ROOT).as_posix() for path in required if path not in payloads]
    if missing:
        raise RuntimeError(f"final release requires metadata files: {missing}")
    placeholder_tokens = (
        b"[Author name]",
        b"[Affiliation]",
        b"[ORCID]",
        b"[Repository URL]",
        b"[Funding statement]",
        b"[Conflict-of-interest statement]",
        b"DOI pending",
    )
    manuscript_paths = [
        PACKAGE_ROOT / "paper/manuscript.md",
        PACKAGE_ROOT / "paper/manuscript.tex",
    ]
    findings = [
        f"{path.relative_to(PACKAGE_ROOT)}: {token.decode('utf-8')}"
        for path in manuscript_paths
        for token in placeholder_tokens
        if path in payloads and token in payloads[path]
    ]
    if findings:
        raise RuntimeError("final manuscript metadata gate failed: " + "; ".join(findings))
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on optional paper extra
        raise RuntimeError(
            "final release validation requires the package's 'paper' dependencies"
        ) from exc
    pdf_path = PACKAGE_ROOT / "output/pdf/okf_rag_preprint.pdf"
    reader = PdfReader(str(pdf_path))
    if not reader.pages:
        raise RuntimeError("final manuscript PDF has no pages")
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages).encode("utf-8")
    pdf_findings = [
        token.decode("utf-8") for token in placeholder_tokens if token in pdf_text
    ]
    if pdf_findings:
        raise RuntimeError(f"final PDF metadata gate failed: {pdf_findings}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--status", choices=("draft", "final"), default="draft")
    parser.add_argument(
        "--source-date-epoch",
        type=int,
        default=int(os.environ.get("SOURCE_DATE_EPOCH", DEFAULT_SOURCE_DATE_EPOCH)),
        help="UTC timestamp used for deterministic manifest and ZIP metadata",
    )
    args = parser.parse_args()
    counts = _validate_completion()
    files = _included_files(excluded_paths={args.manifest, args.archive})
    payloads, transformations = _public_payloads(files)
    _secret_scan(payloads)
    if args.status == "final":
        _validate_final_metadata(payloads)
    inventory = _inventory(payloads)
    created_at = datetime.fromtimestamp(args.source_date_epoch, timezone.utc).isoformat()
    payload = {
        "schema_version": "okf-trial-release-v1",
        "created_at": created_at,
        "source_date_epoch": args.source_date_epoch,
        "artifact_title": "Open Knowledge Format v0.2 as a Retrieval Substrate",
        "release_status": (
            "final_publication_candidate"
            if args.status == "final"
            else "draft_pending_author_and_license_metadata"
        ),
        "file_count": len(inventory),
        "total_uncompressed_bytes": sum(int(item["bytes"]) for item in inventory),
        "inventory_sha256": _inventory_digest(inventory),
        "completion_counts": counts,
        "bundle_content_sha256": "bec2561aa21eb4be38259d04d9aa34ed96b9abd57058fe7d10ce775eded1eb03",
        "okf_spec_commit": "3fcbb9f828c2f23d109c855ee403c3a4c81f3a96",
        "public_copy_transformations": transformations,
        "files": inventory,
    }
    manifest_bytes = _canonical_json_bytes(payload)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_bytes(manifest_bytes)
    _write_reproducible_zip(
        args.archive,
        payloads,
        manifest_bytes,
        source_date_epoch=args.source_date_epoch,
    )
    print(args.manifest)
    print(args.archive)
    print(json.dumps({"files": len(files), "zip_bytes": args.archive.stat().st_size}))


if __name__ == "__main__":
    main()

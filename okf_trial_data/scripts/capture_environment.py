#!/usr/bin/env python3
"""Capture a secret-free software environment manifest for reproducibility."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "okf_trial_data/environment_manifest.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    packages_by_identity = {
        (
            (distribution.metadata["Name"] or distribution.name).casefold(),
            distribution.version,
        ): {
            "name": distribution.metadata["Name"] or distribution.name,
            "version": distribution.version,
        }
        for distribution in importlib.metadata.distributions()
    }
    packages = sorted(
        packages_by_identity.values(),
        key=lambda item: item["name"].casefold(),
    )
    payload = {
        "schema_version": "okf-environment-v1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "python_executable_name": Path(sys.executable).name,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": packages,
        "security_note": "No environment-variable names or values are captured.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    print(f"packages={len(packages)}")


if __name__ == "__main__":
    main()

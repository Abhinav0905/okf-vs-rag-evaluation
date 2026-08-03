# Invalidated and superseded runs

## `superseded_gold_v1_partial`

- Stopped: 2026-08-02, before automated judging or condition-level answer-quality analysis.
- Reason: independent semantic review found inherited reference-answer and evidence-page errors in the frozen benchmark, concentrated in synthetic multi-page items.
- Preserved output: 609 of 1,455 scheduled answer records, with no blank answers or duplicate cells.
- Recorded generation cost: USD 11.752524.
- Disposition: invalidated in full. These answers must not be resumed, judged, pooled with, or substituted into the corrected benchmark run.
- Results inspected before stopping: retrieval-only screening metrics and isolated record-level integrity checks; no raw-versus-OKF answer scores existed.

Preserved file hashes:

- `generation_records.jsonl`: `399130a1593e7179196f6891e47ac6b68b3c327c88f95ab803e3fe4c028557c6`
- `run_manifest.json`: `98549c0c6506238057cc77a60108b226c2047293b890da4a17603b7ea1aa4743`
- `schedule.json`: `befbf1ecf5ed9d2ee96aecd445f9fd3eabff60ef0fba756221a90ab2cbb8b9b1`

The preserved directory is `results/superseded_gold_v1_partial/`. It is retained solely as an audit artifact and is excluded from the publication release archive.

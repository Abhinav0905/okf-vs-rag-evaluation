# Data and artifact licensing

This file covers everything in the release that is **not** source code. The code
is covered by [`LICENSE`](LICENSE).

The release mixes four kinds of material with different origins, and they cannot
all carry the same terms. Each is listed separately below.

## 1. Material created by this study

Applies to: the question set and answer keys in `data/benchmark_questions.json`,
the audit records in `data/gold_audit.jsonl` and `data/gold_audit_summary.json`,
the protocol and review documents in `protocol/`, the analysis outputs in
`results/*/analysis/`, the retrieval and diagnostic summaries, and the
manuscript in `paper/`.

License: **Creative Commons Attribution 4.0 International (CC BY 4.0)**.
<https://creativecommons.org/licenses/by/4.0/>

Attribution should cite the record in [`CITATION.cff`](CITATION.cff).

Note on provenance: the question set is a corrected derivation of two inherited
internal question files, not an independently authored benchmark. The
corrections, exclusions, and their reasons are recorded by question ID in
`data/gold_audit.jsonl` and in the deviations log in
`protocol/EXPERIMENT_PROTOCOL.md`. Blinded human validation of the corrected
labels was **not** completed; see the protocol for exactly what was and was not
checked.

## 2. Extracted passages from the source documents

Applies to: the passage text inside `data/okf_bundles/`, the retrieved-passage
text inside the records in `results/`, and any quoted evidence in the
manuscript.

These are verbatim extracts from Wildfire Mitigation Plans filed by Pacific Gas
and Electric Company, Southern California Edison, and PacifiCorp with the
California Office of Energy Infrastructure Safety. They are reproduced here for
research and verification purposes. They are **not** covered by CC BY 4.0,
because this study does not hold rights in them.

**Redistribution decision.** The author has determined that the PG&E Wildfire
Mitigation Plan is a publicly available document, filed in a public regulatory
proceeding with the California Office of Energy Infrastructure Safety, and that
the extracted passages may therefore be shared for research and verification.
The extracted passage text is included in this release on that basis. The source
document is identified by hash so any reader can obtain and verify the original:

- `pge-2026-2028-base-wmp-vol1-r0.pdf`
- SHA-256 `e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a`

Rights in the underlying document remain with its authors and filers; this study
claims none. Anyone redistributing further should satisfy themselves of the
position for their own use.

The source PDFs themselves are **not** included in the release archive.

## 3. Language-model outputs

Applies to: `answer_text` and citation fields in `generation_records.jsonl`, and
the judge objects in `judge_trial_records.jsonl` and `answer_scores.jsonl`.

These were produced by Anthropic Claude models served through Amazon Bedrock and
are published as experimental evidence so the reported numbers can be
recomputed. Reuse is subject to the terms of the model provider and of Amazon
Bedrock in force at the time of generation. Exact model identifiers, region,
prompts, sampling settings, and execution dates are recorded in the run and
judge manifests.

They are records of model behaviour on a specific date and should not be treated
as verified statements about the source documents.

## 4. Third-party specifications and models referenced

The Open Knowledge Format specification is authored by Google Cloud and is
pinned in this study at commit `3fcbb9f828c2f23d109c855ee403c3a4c81f3a96`. It is
referenced, not redistributed. Embedding, reranking, and generation model
weights and services are likewise referenced by identifier and are governed by
their own licences.

## Excluded from the release

- `.env` and every credential, key, session token, and account identifier.
- Source PDFs.
- `data/titan_embeddings.json` (about 40 MB; regenerate with
  `scripts/run_retrieval_diagnostics.py`).
- `results/superseded_*/` and `tmp/`. The invalidated partial run is described in
  the protocol deviations log; its records are retained locally as an audit trail
  and are deliberately not published as results.

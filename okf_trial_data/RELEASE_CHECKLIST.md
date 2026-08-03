# GitHub, Zenodo, SSRN, and arXiv release checklist

## Author inputs still required

- Final author names and order
- Affiliations and contact email
- ORCID identifiers
- Funding and conflict-of-interest statements
- GitHub owner/repository name
- Code license and data/annotation license
- Confirmation that each source PDF may or may not be redistributed

## Repository hygiene

- [ ] Confirm `.env`, credentials, AWS account IDs, logs containing secrets, and
      local database dumps are excluded.
- [ ] Run the full test suite from a clean environment.
- [ ] Regenerate every table and figure from immutable JSONL records.
- [ ] Verify all hashes in the run, judge, bundle, and release manifests.
- [ ] Confirm the final run and retrieval summary reference the corrected benchmark
      version/hash, and that the superseded partial generation is absent.
- [ ] Include model IDs, region, prompts, dates, prices, dependencies, and seeds.
- [ ] Include raw failures and schema diagnostics, including the superseded pilot
      that motivated structured judge transport, if disclosed in the artifact.
- [ ] Add `LICENSE`, `DATA_LICENSE.md`, `CITATION.cff`, `CODE_OF_CONDUCT.md`,
      and contributor guidance. `DATA_LICENSE.md` must state whether extracted
      source passages and model outputs may be redistributed.
- [ ] Do not redistribute source PDFs without confirmed permission; publish
      hashes and acquisition instructions when redistribution is restricted.

## Manuscript integrity

- [ ] Replace all author/repository/DOI placeholders.
- [ ] Confirm Self-RAG and FLARE are labeled “re-implementation.”
- [ ] Keep OKF-native answer results labeled exploratory.
- [ ] Report absolute scores, paired deltas, 95% confidence intervals, exact
      denominators, unadjusted p-values, and Holm-adjusted p-values.
- [ ] Report null or negative findings directly.
- [ ] Add a blinded human-validation sample before strong answer-quality claims.
- [ ] Repeat the scholarly prior-art search immediately before submission.
- [ ] Render the final PDF and visually inspect every page.
- [ ] Compile `paper/manuscript.tex` from the self-contained `paper/figures/`
      directory in a clean TeX environment suitable for arXiv.

## Recommended publication order

1. Freeze the code and artifact contents in a Git commit.
2. Run `scripts/build_release.py --status final` twice with the same
   `SOURCE_DATE_EPOCH` and verify identical archive SHA-256 values.
3. Create a version tag and GitHub release candidate.
4. Archive that exact release in Zenodo and reserve/mint the DOI.
5. Insert the DOI and final GitHub URL into the manuscript and metadata.
6. Create a final patch release if the DOI insertion changes the archive, using
   the Zenodo concept DOI for all-version citation when appropriate.
7. Submit the research-paper version to arXiv (`cs.IR`, optional `cs.CL`
   cross-list) and/or the polished PDF to SSRN.
8. Link the arXiv/SSRN identifier from GitHub and Zenodo metadata.

Do not mint the DOI until authorship, licensing, and the exact public artifact
contents are approved. DOI metadata is public and should not contain draft or
private information.

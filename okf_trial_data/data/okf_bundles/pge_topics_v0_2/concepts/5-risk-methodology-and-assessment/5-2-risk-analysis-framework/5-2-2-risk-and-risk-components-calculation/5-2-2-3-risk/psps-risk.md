---
type: Document Section
title: PSPS Risk
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=psps-risk
tags:
- document-section
- corpus-pge
- level-5
status: stable
generated:
  by: process:okf-trial-topic-bundle-v1
  at: '2026-08-02T00:00:00Z'
sources:
- id: source-pdf
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=104,105
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00063
slug: psps-risk
outline_level: 5
outline_order: 63
section_number: null
section_path:
- 5. Risk Methodology and Assessment
- 5.2 Risk Analysis Framework
- 5.2.2 Risk and Risk Components Calculation
- 5.2.2.3 Risk
- PSPS Risk
page_number: 104
page_numbers:
- 104
- 105
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: 9c8c22c65ecdd751a0b6f80ca48fd42a6385c83e5c1bc7ceade0e5d59f89595f
child_count: 0
---

# PSPS Risk

## Evidence

<!-- okf-trial:evidence-start -->
PG&E calculates PSPS risk at the segment circuit level.  As described in previous 
sections, PSPS likelihood and PSPS consequence are calculated by the probability and 
consequence of each individual customer service_point_ID (SPID).  Those calculations 
provide the PSPS risk score per customer.  The risk score represents annual dollarized 
reliability risk related to PSPS events, accounting for frequency of events, duration and 
customer impacts.

-74-

The customer risk score is then applied to a critical customer weighting that is based on 
their customer classification.  Lastly, all customer risk scores are aggregated to 
determine the overall PSPS risk score.

The following formulas display how to calculate the PSPS risk, likelihood and 
consequence at the segment circuit level:

Consequence uses a likelihood-weighted consequence, and the likelihood is summed 
up across SPIDs.  The total PSPS risk is then divided by the total likelihood to derive 
the consequence for that circuit segment.

The results of the PSPS Consequence Model are then calibrated to PG&E’s Enterprise 
Risk Model’s CBA risk score for PSPS.

EPSS Outage Risk
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [5.2.2.3 Risk](../5-2-2-3-risk.md)
* Previous topic: [Outage Program Risk](outage-program-risk.md)
* Next topic: [EPSS Outage Risk](epss-outage-risk.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 104-105.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 104-105.

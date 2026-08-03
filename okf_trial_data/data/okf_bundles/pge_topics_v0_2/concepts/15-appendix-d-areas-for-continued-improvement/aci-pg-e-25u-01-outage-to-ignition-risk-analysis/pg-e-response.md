---
type: Document Section
title: 'PG&E Response:'
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=pg-e-response
tags:
- document-section
- corpus-pge
- level-3
status: stable
generated:
  by: process:okf-trial-topic-bundle-v1
  at: '2026-08-02T00:00:00Z'
sources:
- id: source-pdf
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=592,593,594
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00928
slug: pg-e-response
outline_level: 3
outline_order: 928
section_number: null
section_path:
- Appendix D – Areas for Continued Improvement
- ACI PG&E-25U-01 – Outage to Ignition Risk Analysis
- 'PG&E Response:'
page_number: 592
page_numbers:
- 592
- 593
- 594
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: 3e40b136fb3a8fe475129749213db2bb0058917527d11f9271775c37fd5801a9
child_count: 0
---

# PG&E Response:

## Evidence

<!-- okf-trial:evidence-start -->
The WDRM v4 probability of ignition model does distinguish by outage type.

Specifically, the WDRM v4 includes the introduction of event cause and equipment type 
interaction terms to the Probability of Ignition given Outage (p(i|o)) model to improve 
performance for causal pathways that share underlying characteristics for weather and 
fuels.  To achieve this, an expanded set of Pf/Outage causal models has been 
developed.  The p(i|o) model correlates to failure/outage rates, weather conditions, fuel 
conditions and availability, and other location-specific attributes.  However, the 
correlation between fuel and weather conditions and ignition outcomes also depends on 
the nature of the underlying events.  Specifically, some events, like transformer failures 
predominantly result in pole fires that are not influenced by fuels on the ground, while 
others, like insulator tracking faults, require moisture and condensation for an event to 
occur.  The introduction of event cause and equipment type labels for events allowed 
the use of interaction terms that produce separate weather and fuels correlation terms 
for distinct groups of events that share the same characteristics.  An important purpose 
for the p(i|o) model is to support tradeoffs between mitigation strategies.

Table ACI-PG&E-25U-01-1 below outlines the twelve individual p(i|o) sub-models and 
their correlation to the 22 probability of outage models.  More details on the 
development and technical basis of these sub models are available in the DEPM v4 
Documentation,247 Section 3.6 Probability of Ignition Model, pp. 81-86.

247 The supporting document is available at:  PG&E’s Community Wildfire Safety Program.

-562-

TABLE ACI-PG&E-25U-01-1:   
CORRELATION BETWEEN SUB MODELS AND OUTAGE MODELS 105

The p(i|o) model produces separate weather and fuels correlation terms for distinct 
groups of events that share the same characteristics.

An important purpose for the p(i|o) model is to support tradeoffs between mitigation 
strategies, including EPSS.  Therefore, the v4 p(i|o) model needed to be calibrated to 
predict the number of ignitions that would be expected without EPSS.  Section 3.3 
explains how the ignitions event training data was modified to account for EPSS 
impacts.

-563-

ACI PG&E-23B-03 – Incorporation of Extreme Weather Scenarios in Planning
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [ACI PG&E-25U-01 – Outage to Ignition Risk Analysis](../aci-pg-e-25u-01-outage-to-ignition-risk-analysis.md)
* Previous topic: [Section and Page Number of Any Improvements:](section-and-page-number-of-any-improvements.md)
* Referenced section: [3.6 Projected Expenditures](../../3-overview-of-wmp/3-6-projected-expenditures.md)
* Referenced section: [3.3 Utility Mitigation Activity Tracking IDs](../../3-overview-of-wmp/3-3-utility-mitigation-activity-tracking-ids.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 592-594.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 592-594.

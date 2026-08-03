---
type: Document Section
title: EPSS Outage Risk
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=epss-outage-risk
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=105,106
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00064
slug: epss-outage-risk
outline_level: 5
outline_order: 64
section_number: null
section_path:
- 5. Risk Methodology and Assessment
- 5.2 Risk Analysis Framework
- 5.2.2 Risk and Risk Components Calculation
- 5.2.2.3 Risk
- EPSS Outage Risk
page_number: 105
page_numbers:
- 105
- 106
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: c151817f9bbfbcaf2df696e1148e206072d2915abd89257e012230deb17a5c94
child_count: 0
---

# EPSS Outage Risk

## Evidence

<!-- okf-trial:evidence-start -->
The goal of the EPSS outage risk model is to determine the amount of additional risk 
incurred when EPSS is enabled.  Therefore, EPSS outage risk is the outage risk when 
EPSS is enabled minus the baseline outage risk that exists without EPSS.  As a result, 
we need to determine the risk of an outage with and without EPSS enabled.

epss_riskcs =risk_with_epss_enabledcs −risk_with_epss_disabledcs

-75-

Where:

cs 
circuit segment

m 
asset type

CEPSS_enabledsustained outages, m, cs 
consequence of EPSS-enabled sustained outages for each 
IGP asset type on circuit segment (conductor, support 
structure)

s 
subset (WDRM)

NEPSS_enabledsustained outages, m(s),cs 
Number of expected sustained outages when EPSS is 
enabled for WDRM subset mapped to IGP Model asset 
type (conductor, support structure)

∑m∈asset_types 
Sum across all IGP asset types (conductor, support 
structure)

5.2.3 
Key Assumptions and Limitations
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [5.2.2.3 Risk](../5-2-2-3-risk.md)
* Previous topic: [PSPS Risk](psps-risk.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 105-106.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 105-106.

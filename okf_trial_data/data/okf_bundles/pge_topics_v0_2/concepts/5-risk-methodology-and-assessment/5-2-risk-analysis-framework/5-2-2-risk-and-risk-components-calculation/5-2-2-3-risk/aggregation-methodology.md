---
type: Document Section
title: Aggregation Methodology
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=aggregation-methodology
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=101,102
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00058
slug: aggregation-methodology
outline_level: 5
outline_order: 58
section_number: null
section_path:
- 5. Risk Methodology and Assessment
- 5.2 Risk Analysis Framework
- 5.2.2 Risk and Risk Components Calculation
- 5.2.2.3 Risk
- Aggregation Methodology
page_number: 101
page_numbers:
- 101
- 102
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: 85ba55a3f5e7a16916c06349bc24a58a47e4c29e9cfe5cc8b1739b92e2ca5681
child_count: 0
---

# Aggregation Methodology

## Evidence

<!-- okf-trial:evidence-start -->
Circuit segment aggregation sums up all the potential risk that was modeled along the 
length of a segment.  Figure PG&E-5.2.2.3-1 shows an example of two circuit segments 
that intersect multiple grid pixels and have multiple assigned equipment assets ( ).  For 
geospatial models, this pixel risk for any pixel that is intersected by a circuit segment is 
summed to determine the aggregated pixel risk.  For asset models, the risk for each 
asset belonging to the circuit segment is summed to determine the aggregated asset 
risk.  Finally, the summed pixel and asset risks can in turn be summed to calculate the 
total aggregated circuit segment risk.

FIGURE PG&E-5.2.2.3-1:  
CIRCUIT SEGMENT AGGREGATION 21

-71-

Shared pixels and assets complicate circuit segment aggregation of risk.  In 
Figure PG&E-5.2.2.3-1 the two circuit segments share a common pixel, F6, and a 
support structure (pole) asset also located in pixel F6.  To keep the total sum of risk on 
the network constant, these shared risk results must be partially distributed to each of 
the circuit segments.  The aggregation methodology, in this case, would assign half of 
the F6 pixel risk and half of the support structure risk to each of the circuit segments.

Compositing Event Models
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [5.2.2.3 Risk](../5-2-2-3-risk.md)
* Previous topic: [Ignition (Wildfire) Risk](ignition-wildfire-risk.md)
* Next topic: [Compositing Event Models](compositing-event-models.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 101-102.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 101-102.

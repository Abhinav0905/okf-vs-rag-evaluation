---
type: Document Section
title: Modularization
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=modularization
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=140
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00085
slug: modularization
outline_level: 5
outline_order: 85
section_number: null
section_path:
- 5. Risk Methodology and Assessment
- 5.6 Quality Assurance and Quality Control
- 5.6.2 Model Controls, Design, and Review
- Risk Model Development Process
- Modularization
page_number: 140
page_numbers:
- 140
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: 80e45b394d95d3fe03f9244137c77366c3203722465d47bb3e492348bf84854a
child_count: 0
---

# Modularization

## Evidence

<!-- okf-trial:evidence-start -->
The risk models are designed to employ multiple layers of modularization to manage 
changes and enhancements.  As outlined in Section 5.2, the WDRM and the WTRM are 
comprised of two core modules:  a Consequence model and a set of Event Probability 
models.

The Event Probability models support the distribution and transmission by predicting 
where electrical assets are most likely to experience an abnormal operating event that 
results in an outage or ignition event.  Event Probability models generally fall into 
two categories:  Equipment Asset and Contact From Object models.

Equipment Asset Models consider event history and contributing factors to predict 
failure of specific types of electrical equipment.  Each asset model uses a unique set of 
inputs (covariates) from a pool of asset attributes and environmental conditions.  For 
some assets, unique causal models (sub-sets), are produced for specific types of 
failures.

Contact From Object Models consider event history and contributing factors to predict 
failure caused by contact from foreign objects with electrical assets.  Each contact 
model uses a unique set of inputs (covariates) from a pool of object attributes and 
environmental conditions.  All contact models provide unique causal models (sub-sets) 
for specific types of contact failures.

The WFC Model supports the WDRM and WTRM by estimating the likely outcome of an 
ignition originating at the geographical location of any electrical asset.  The 
consequence model is trained to historical fires, while considering:  Technosylva fire 
simulations, PG&E Meteorology’s FPI index, dry wind conditions, and other fuel and 
weather conditions.  In addition, the consequence estimates are adjusted for population 
Egress and fire-fighting Suppression impacts.

Reanalysis
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [Risk Model Development Process](../risk-model-development-process.md)
* Next topic: [Reanalysis](reanalysis.md)
* Referenced section: [5.2 Risk Analysis Framework](../../../5-2-risk-analysis-framework.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, page 140.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, page 140.

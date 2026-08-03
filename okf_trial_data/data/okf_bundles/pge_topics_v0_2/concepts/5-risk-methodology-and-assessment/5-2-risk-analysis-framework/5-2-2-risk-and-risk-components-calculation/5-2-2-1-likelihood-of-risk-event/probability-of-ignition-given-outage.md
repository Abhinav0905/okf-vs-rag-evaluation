---
type: Document Section
title: Probability of Ignition Given Outage
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=probability-of-ignition-given-outage
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=90,91
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00046
slug: probability-of-ignition-given-outage
outline_level: 5
outline_order: 46
section_number: null
section_path:
- 5. Risk Methodology and Assessment
- 5.2 Risk Analysis Framework
- 5.2.2 Risk and Risk Components Calculation
- 5.2.2.1 Likelihood of Risk Event
- Probability of Ignition Given Outage
page_number: 90
page_numbers:
- 90
- 91
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: a6dab46be9ddf866eb5d5edcc3a76f8f4e4f62ac31ba0daa90b3301deb9e772d
child_count: 0
---

# Probability of Ignition Given Outage

## Evidence

<!-- okf-trial:evidence-start -->
The Probability of Ignition Given Outage model, p(i|o), takes as its input the probability 
of outage, p(o), results from an Asset Equipment or Contact From Object model.  The 
percentage of outages that result in an ignition varies on the outage type.  The p(i|o) 
model uses failure model-specific attributes and environmental conditions to determine 
the likelihood that a given outage is likely to result in an ignition.

For asset-based event models, the probability of ignition for a given asset is the product 
of its probability of ignition given an outage and its probability of an outage:

𝑝𝑝(𝑖𝑖)𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎= 𝑝𝑝(𝑖𝑖|𝑜𝑜)𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎∗𝑝𝑝(𝑜𝑜)𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎

For Contact From Object models, which are location, pixel-based models, the 
probability of ignition for a given location is the product of the location probability of 
ignition given outage and the location probability of outage for a specific model:

𝑝𝑝(𝑖𝑖)𝑙𝑙𝑙𝑙𝑙𝑙= 𝑝𝑝(𝑖𝑖|𝑜𝑜)𝑙𝑙𝑙𝑙𝑙𝑙∗𝑝𝑝(𝑜𝑜)𝑙𝑙𝑙𝑙𝑙𝑙

-60-

Individual asset and contact from object probabilities can be composited to determine a 
summed probability of ignition for an asset or location:

Where:

asset 
Modeled asset type:  conductor, transformer, support structure, etc.

loc 
Asset location expressed as a 100 meter square pixel within the PG&E service 
territory

p(i) 
Probability of Ignition

p(i|o) 
Probability of Ignition given an Outage

p(o) 
Probability of Outage
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [5.2.2.1 Likelihood of Risk Event](../5-2-2-1-likelihood-of-risk-event.md)
* Previous topic: [Ignition Likelihood (Probability of Ignition) for Distribution](ignition-likelihood-probability-of-ignition-for-distribution.md)
* Next topic: [Ignition Likelihood (Probability of Ignition) for Transmission](ignition-likelihood-probability-of-ignition-for-transmission.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 90-91.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 90-91.

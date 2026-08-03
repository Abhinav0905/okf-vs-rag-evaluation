---
type: Document Section
title: Ignition Likelihood (Probability of Ignition) for Transmission
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=ignition-likelihood-probability-of-ignition-for-transmission
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=91,92,93
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00047
slug: ignition-likelihood-probability-of-ignition-for-transmission
outline_level: 5
outline_order: 47
section_number: null
section_path:
- 5. Risk Methodology and Assessment
- 5.2 Risk Analysis Framework
- 5.2.2 Risk and Risk Components Calculation
- 5.2.2.1 Likelihood of Risk Event
- Ignition Likelihood (Probability of Ignition) for Transmission
page_number: 91
page_numbers:
- 91
- 92
- 93
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: 7cde4fdfb9fc0c789c3dff33e76b03316fe313db0d374dff87181eccfd52e8eb
child_count: 0
---

# Ignition Likelihood (Probability of Ignition) for Transmission

## Evidence

<!-- okf-trial:evidence-start -->
Figure 5-2-2 provides a schematic overview of the transmission probability of ignition 
calculation.

FIGURE 5-2-2:  
TRANSMISSION IGNITION LIKELIHOOD CALCULATION SCHEMATIC 14

The transmission probability of ignition model uses a mix of first principle and machine 
learning (ML) probability of failure causal models.

-61-

First principle causal models are implemented as fragility curves optimized for a specific 
threat.  The underlying first principle relationships set the shape of the fragility curve.  
Figure PG&E-5.2.2.1-1 presents an example causal fragility curve.

FIGURE PG&E-5.2.2.1-1:  
TRANSMISSION PROBABILITY OF FAILURE FRAGILITY CURVE 15

ML causal models directly estimate probability of failure values in the same manner as 
the distribution probability models.  Also, like distribution, the sums of predicted 
transmission asset probability of failures are calibrated to match annual historical failure 
rates.  The annualized transmission asset probability of failure serves as a proxy for the 
probability of ignition.  The need for a probability of ignition proxy value is driven by the 
very low annual number of transmission asset-related ignitions.

The probability of ignition assigned at a transmission support structure location is 
proxied as the sum of the probability of failures from a composite of the first principle 
and ML causal model results:

Where:

ss 
Support Structure

fpm 
First-Principle Model for Probability of Failure

ML 
Machine Learning model for Probability of Failure

p(f) 
Probability of Failure

p(i) 
Probability of Ignition

-62-

Burn Likelihood
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [5.2.2.1 Likelihood of Risk Event](../5-2-2-1-likelihood-of-risk-event.md)
* Previous topic: [Probability of Ignition Given Outage](probability-of-ignition-given-outage.md)
* Next topic: [Burn Likelihood](burn-likelihood.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 91-93.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 91-93.

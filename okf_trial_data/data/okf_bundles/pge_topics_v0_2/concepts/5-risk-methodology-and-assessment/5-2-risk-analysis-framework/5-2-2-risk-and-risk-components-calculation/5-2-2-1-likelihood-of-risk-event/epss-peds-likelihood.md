---
type: Document Section
title: EPSS (PEDS) Likelihood
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=epss-peds-likelihood
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=94,95,96
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00050
slug: epss-peds-likelihood
outline_level: 5
outline_order: 50
section_number: null
section_path:
- 5. Risk Methodology and Assessment
- 5.2 Risk Analysis Framework
- 5.2.2 Risk and Risk Components Calculation
- 5.2.2.1 Likelihood of Risk Event
- EPSS (PEDS) Likelihood
page_number: 94
page_numbers:
- 94
- 95
- 96
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: 701bbe4638f77dcf9e5c7bdd7586b88517de0157825f55a406163f9c2d48413d
child_count: 0
---

# EPSS (PEDS) Likelihood

## Evidence

<!-- okf-trial:evidence-start -->
Figure 5-2-4 provides a schematic overview of the EPSS risk calculation from likelihood 
and consequence.

FIGURE-5-2-4:  
EPSS RISK CALCULATION PROCEDURE SCHEMATIC 17

EPSS devices are enabled on powerlines when the risk of wildfire is high.  Without 
EPSS, if a tree branch were to fall on a powerline, the recloser would attempt to 
re-establish power.  When EPSS is enabled, the recloser is limited to attempting to  
re-establish power for only 60 milliseconds.  If it cannot re-establish power within that 
timeframe, the power will remain off, resulting in fewer wildfires in high-risk areas.  
EPSS enablement does not increase the number of faults but does increase the number 
of sustained outages as probable momentary outages can become sustained outages.

The goal of the EPSS outage risk model is to determine the amount of additional risk 
from EPSS enablement.  EPSS outage risk is the outage risk when EPSS is enabled 
minus the baseline outage risk that exists without EPSS as shown in 
Figure PG&E-5.2.2.1-2.  This model help determine the likelihood of an outage with and 
without EPSS enabled.

-64-

FIGURE PG&E-5.2.2.1-2:  
EPSS AND BASELINE OUTAGE RISK 18

The likelihood of an EPSS-enabled sustained outage on a circuit segment is estimated 
based on the portion of the wildfire season when EPSS is enabled and the expected 
number of sustained outages, as calculated from WDRM v4 event probability models.  
Our EPSS outages dataset reveals that out of approximately 8,000 outages with EPSS 
enabled, all but a few outages were sustained outages.  Therefore, when EPSS is 
enabled, any fault is assumed to result in a sustained outage.

N EPSS_enabledsustainedoutages, s, cs = 𝑓𝑓 EPSS_enabled, cs ∗ N outages, s, cs

Where:

cs 
circuit segment

s 
WDRM event probability model

NEPSS_enabledsustainedoutages,s, cs 
number of expected sustained outages per WDRM event 
probability model when EPSS is enabled for a circuit 
segment

N outages, s, cs 
expected outage count from each WDRM event probability 
model on a circuit segment

𝑓𝑓 EPSS_enabled, cs 
fraction of wildfire season EPSS is enabled on a circuit 
segment

The EPSS Outage Risk model also considers the fraction of failures that turn into 
sustained outages when EPSS is not enabled so that the baseline outage risk can be 
subtracted from the EPSS enabled risk.  To determine this, we factor in the portion of 
time when EPSS is enabled on a circuit segment, number of expected outages for a 
WDRM subset on the circuit segment, and the fraction of sustained outages out of the 
total number of outages.  When EPSS is enabled, this same event would result in a 
sustained outage.

-65-

N sustainedoutages,s,csEPSS_disabled = 𝑓𝑓 EPSS_enabledcs * N outages,s,cs * 𝑓𝑓 sustained,s

Where:

cs 
circuit segment

𝑓𝑓 EPSS_enabled, cs 
fraction of wildfire season when EPSS is 
enabled for a circuit segment

s 
subset

N outages,s,cs 
expected outage count for each subset on 
circuit segment (provided by WDRM)

Nsustainedoutages,s,csEPSSdisabled 
Number of sustained outages for each 
WDRM subset on circuit segment when 
EPSS is disabled

𝑓𝑓 sustained, s 
number of sustained outages divided by total 
number of outages for WDRM subset on a 
circuit segment

Historically, the fraction of sustained outages out of total outages accounts for roughly 
85 percent of outages in HFTD/HFRA.

5.2.2.2 
Consequence of Risk Event
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [5.2.2.1 Likelihood of Risk Event](../5-2-2-1-likelihood-of-risk-event.md)
* Previous topic: [PSPS Likelihood](psps-likelihood.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 94-96.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 94-96.

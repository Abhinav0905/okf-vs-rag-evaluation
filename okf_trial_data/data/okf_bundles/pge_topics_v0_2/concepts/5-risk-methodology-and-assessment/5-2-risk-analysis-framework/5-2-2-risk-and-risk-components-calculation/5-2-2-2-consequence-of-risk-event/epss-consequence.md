---
type: Document Section
title: EPSS Consequence
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=epss-consequence
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=99,100
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00054
slug: epss-consequence
outline_level: 5
outline_order: 54
section_number: null
section_path:
- 5. Risk Methodology and Assessment
- 5.2 Risk Analysis Framework
- 5.2.2 Risk and Risk Components Calculation
- 5.2.2.2 Consequence of Risk Event
- EPSS Consequence
page_number: 99
page_numbers:
- 99
- 100
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: 887712411ea889fe933d0a925d4d39fea210b8f5fe3aced7f6b67213c5cf7c6b
child_count: 0
---

# EPSS Consequence

## Evidence

<!-- okf-trial:evidence-start -->
The consequence of a sustained outage on a circuit segment is estimated CMI times 
the value of service for the customers on that circuit segment.  Typically, when EPSS is 
enabled, more customers lose power during an outage.  This is because a fault will 
extend upstream to the nearest EPSS-enabled protective device rather than the nearest 
protective device.  PG&E data shows that the duration of an outage is not significantly 
different whether or not EPSS is enabled.  When EPSS is enabled, the CMI is the 
duration of the outage times the number of customers impacted for the enabled circuit 
segment.  The overall value of service for a circuit segment is the weighted average of 
the value of service for each customer class (Residential, Small Commercial & 
Industrial, and Medium Commercial & Industrial) by the number of customers in each 
class.

VOScs = ∑c∈{RES, SMALL C&I, MEDIUM C&I} VOSc  * Nc,cs /Ncs

Where:

Ncs 
number of circuit segments

Nc,cs 
number of customers per class on circuit segment

VOSc 
value of service per customer class (see Table PG&E-5.2.2-2  
above)

∑c∈{RES, SMALL C&I, MEDIUM C&I} 
summation of customers across all classes

VOScs 
value of service on a circuit segment

CEPSS_enabledsustainedoutages,m,cs = Dsustainedoutage,m,cs  * NEPSS_enabledcustomers,m,cs * VOScs

-69-

Where:

cs 
circuit segment

CEPSS_enabledsustained 
outages, m, cs

consequence of EPSS-enabled sustained outages across circuit 
segment asset types

Dsustained outage, m, cs 
duration of sustained outages across circuit segment asset types

m 
asset type (Integrated Grid Planning (IGP) Model)

NEPSS_enabledcustomers, m,cs 
number of EPSS-enabled customers across asset types on a 
circuit segment

VOScs 
value of service on a circuit segment

The expected duration of an EPSS-enabled sustained outage on a circuit segment is 
calculated by taking a weighted average of the sum of all assets (a) of IGP Model asset 
types and their upstream protective devices on the circuit segment.

Dsustainedoutage,m,cs = 1/Nm,cs ∑ a in cs and of type m Da(mp)

Where:

a 
asset

cs 
circuit segment

Da(m,p) 
duration of asset outage per asset type and protective device

m 
asset type (i.e., conductor, support structure)

Nm,cs 
number of individual assets of type (m) on a circuit segment

p 
protective device (breaker, Dynamic Protection Device (DPD), 
fuse, switch)

∑ a in cs and of type m 
sum asset outage across all asset types on circuit segment

5.2.2.3 
Risk
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [5.2.2.2 Consequence of Risk Event](../5-2-2-2-consequence-of-risk-event.md)
* Previous topic: [PSPS Consequence](psps-consequence.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 99-100.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 99-100.

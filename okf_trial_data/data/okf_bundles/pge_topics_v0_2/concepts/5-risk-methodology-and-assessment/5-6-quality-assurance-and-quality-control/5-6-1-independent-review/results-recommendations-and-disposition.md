---
type: Document Section
title: 'Results, Recommendations, and Disposition:'
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=results-recommendations-and-disposition
tags:
- document-section
- corpus-pge
- level-4
status: stable
generated:
  by: process:okf-trial-topic-bundle-v1
  at: '2026-08-02T00:00:00Z'
sources:
- id: source-pdf
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=135,136
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00080
slug: results-recommendations-and-disposition
outline_level: 4
outline_order: 80
section_number: null
section_path:
- 5. Risk Methodology and Assessment
- 5.6 Quality Assurance and Quality Control
- 5.6.1 Independent Review
- 'Results, Recommendations, and Disposition:'
page_number: 135
page_numbers:
- 135
- 136
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: 5a6cf8936f80d79e38f6508f23b8af853054fe66b410e43801b49e7956d14720
child_count: 0
---

# Results, Recommendations, and Disposition:

## Evidence

<!-- okf-trial:evidence-start -->
An independent review of the WDRM v4 was performed by Energy & Environmental 
Economics (E3).  Their report, “E3 Review of PG&E’s Wildfire Risk Model Version 4” 
was issued in July 2024.  Some key statements from the report:

Over the last several years, PG&E has continued to improve upon their wildfire risk 
modeling framework and has built a suite of models that is capable of systematically 
quantifying the wildfire risk across their system, frequently going above and beyond 
requirements.

PG&E should continue development of the model to inform the entire risk planning 
decision space, building on v4 to produce transparent and justifiable company-wide 
mitigation budgets for short- and long-term planning.  While we continue to believe that 
the combination of informed risk modeling and experienced SME’s provides a robust 
risk management framework, we also believe that the models, as they become more 
informative, should have an increasing role in the decision-making process.

E3 suggested two areas for improvement of the WDRM:

1) Incorporate temporal dimension in all Sub-Models (Event Probability Models)

Including a temporal dimension into a ML model allows for the integration of time 
dependent data, such as seasonal variations in weather and degradation of assets, 
which improves the accuracy and reliability of forecasts.  The PG&E team has 
already made good progress in this area by updating the Equipment models to 
allow for a temporal dimension.  E3 suggests that this improvement be expanded to 
the other models within the WDRM to further boost performance.  For instance, this 
would allow the Vegetation model to be aware of the time that has passed since an 
area had last undergone maintenance.

2) Evaluate the overall effects of implementing p(i|o)

During discussions with the WDRM team over recent model results, it was shown 
that in some cases adding the step to calculate the probability of ignition given 
outage, P(I|O), reduced the predictive performance relative to the probability of 
outage, P(O), alone.  For instance, this was the case for the 
“primary_conductor_wire_down_cause” subset.  The loss of predictive performance 
for some subsets should be carefully examined, especially in cases where the 
subset may be a large contributor to ignitions (e.g., primary conductors).  In line with 
E3’s overarching recommendation of “right-sizing development efforts” E3 suggests 
that PG&E evaluate the effectiveness of this modeling direction, and reprioritize it as 
needed

-105-

Routine Review Schedule:
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [5.6.1 Independent Review](../5-6-1-independent-review.md)
* Next topic: [Routine Review Schedule:](routine-review-schedule.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 135-136.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 135-136.

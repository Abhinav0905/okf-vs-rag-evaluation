---
type: Document Section
title: Summary
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=summary
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=494,495,496
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00839
slug: summary
outline_level: 4
outline_order: 839
section_number: null
section_path:
- 10. Situational Awareness and Forecasting
- 10.6 Fire Potential Index
- 10.6.1 Existing Calculation Approach and Use
- Summary
page_number: 494
page_numbers:
- 494
- 495
- 496
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: e2997e49229c0ddea9e14aaf93976bbb9a4746001aa7d52eb361342655df22de
child_count: 0
---

# Summary

## Evidence

<!-- okf-trial:evidence-start -->
The FPI is a PG&E model developed to understand the potential for large and 
catastrophic fires to occur across the PG&E service territory.  The first FPI was 
developed in 2015 and has been enhanced significantly over several iterations since.  
The latest model iteration model is called the FPI 5.0 model, which is Version 5 and the 
most accurate model to date.

FPI informs operational decision making of PSPS and EPSS and informs crews what 
precautions must be taken to reduce the risk of fires as directed by utility standards.  
FPI is also a key input into the consequence formulation of PG&E’s planning models 
(Wildfire Distribution Risk Model (WDRM), WRTRM) that inform key long term wildfire 
risk programs of undergrounding and system hardening prioritization.  Improvements in 
FPI model accuracy allows for greater operational mitigation of utility caused wildfire risk 
through PSPS and EPSS for a given customer impact, and better strategic prioritization 
of undergrounding and other wildfire risk mitigations.

Below is a short history on the evolution of FPI models since 2015 that showcases 
PG&E’s continuous improvement efforts through multiple WMP cycles.

PG&E received daily fire danger ratings directly from external sources up until 
December 31, 2014, when the service was disabled at the external source.  In 2015, 
PG&E evaluated multiple public sources and methodologies for fire danger rating and 
benchmarked with SDG&E on their deployment of an FPI using high-resolution weather 
and fuel model data.  In addition, PG&E scientists took instructor-led advanced courses 
in fire danger rating offered by the National Wildfire Coordinating Group to understand 
agency best practices and methodologies to evaluate fire danger.  The early 
development work of FPI and Numerical Weather Prediction (POMMS project) is 
discussed in detail in PG&E’s Electric Program Investment Charge (EPIC) 1.05 project 
report.175  This led to the Version 1 FPI model, which leveraged the National Fire 
Danger Rating System (FPI 1.0).

In 2018, PG&E produced FPI 2.0, which was an index-based model that combined 
weather, fuels and a green-up component called the enhanced vegetation index.  Its 
formulation was closely modeled after SDG&E’s FPI and valuable benchmarking with 
SDG&E meteorologists and scientists.

FPI 3.0 was produced in 2019 by coupling the weather and fuels data around the 
ignition of each fire in the USFS’s Fire Program Analysis – Fire-Occurrence Database 
(FPA-FOD).  This was the first iteration of a machine learning model that used historical 
fire occurrence data with a logistic regression framework.  The end goal was to create 
an FPI model that could predict, based on forecasted weather and fuels conditions, the 
probability of a large fire given an ignition instead of an FPI index value related to the 
risk.  The 2019 FPI model was a function of several quantifiable factors: the LFM, the 
Nelson DFM 10 hour, the Fosberg Fire Weather Index and Land Use.

175 PG&E’s Electric Program Investment Charge 1.05 Project Report, available at:  
https://www.pge.com/assets/pge/docs/about/corporate-responsibility-and-sustainability/PG
E-EPIC-Project-1.05.pdf.

-464-

The FPI 4.0 model was deployed in August 2021 and operated through July 31, 2024.  
It leveraged a novel machine learning framework, additional model features and a fire 
occurrence dataset developed by Sonoma Technology.  Data scientists, meteorologists, 
and fire scientists tested dozens of new model features and various models.  Among the 
model-types tested were logistic regression and multiple machine-learning classification 
model types.  Model results were tested using a train-test split ratio of 
70 percent-30 percent.  The 4.0 model is discussed in detail in PG&E’s 2022 and 2023 
WMP public filings.

During each iteration, the goal has been to increase FPI accuracy by testing additional 
model features, model frameworks (e.g., logistic regression versus more advanced 
machine learning models such as decision trees and gradient boosting) and improving 
or creating input datasets.  The sections below discuss improvements made across 
these elements for FPI 5.0

The FPI 5.0 model was developed in 2022 and 2023 and approved for operations 
starting August 2024 and has several enhancements and improved skill over FPI 4.0. 
The key enhancements include:

• 
Addition of fire radiative power (McClure, et.  al., 2023) for FPI classes to better 
identify catastrophic fires based not only by rapid growth, but also high intensity, 
which is found to be key to explaining fires resulting in structure loss and more likely 
to escape containment;

• 
Expanded model training data to use all detects rather than only the first fire detect, 
this required careful consideration of formulation of sample weights used in model 
training based on the detection order to weight earlier detects more than later 
detects;

• 
Improved spatial relations of weather, fuel moisture, fuels, and terrain data by 
spatially relating satellite fire detection polygon shapes with model data rather than 
using points to represent fires;

• 
Finer spatial resolution of 0.7km2 hexagons to capture greater detail of terrain and 
fuel categories compared to the previous 2x2 km (4 km2) grid cell aggregation of 
fuels and terrain;

• 
Improved temporal resolution and coupling of satellite fire detected fire growth and 
temporal relations to weather and fuel moisture features by using Governance 
Oversight Execute Support (GOES) detects when available; and

• 
New weather and fuel moisture input features including soil moisture, enhanced 
dead and LFM models, new herbaceous fuel moisture model, solar radiation, and 
new fuel properties features added including fuel bed depth and fuel complexity.

-465-

The FPI model is trained on a novel fire occurrence dataset (McClure et al., 2023)176 
that combines sub-daily to hourly fire growth from satellite fire detections from Visible 
Infrared Imaging Radiometer Suite (VIIRS) and GOES where available with agency fire 
information.  The FPI model combines fire weather, dead and LFM, topography and fuel 
types to predict the probability of small, large, critical or catastrophic fire potential.

The weather and fuel moisture features are sourced from PG&E’s 30+ year 
down-scaled climatology available hourly at a 2x2 km resolution, referenced earlier in 
this document.  The fuel categories and topography features from Technosylva are 
aggregated to a new finer spatial resolution of 0.7km2 hexagons using the h3 
opensource framework developed by Uber.

Calculating the FPI and Model Assumptions
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [10.6.1 Existing Calculation Approach and Use](../10-6-1-existing-calculation-approach-and-use.md)
* Next topic: [Calculating the FPI and Model Assumptions](calculating-the-fpi-and-model-assumptions.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 494-496.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 494-496.

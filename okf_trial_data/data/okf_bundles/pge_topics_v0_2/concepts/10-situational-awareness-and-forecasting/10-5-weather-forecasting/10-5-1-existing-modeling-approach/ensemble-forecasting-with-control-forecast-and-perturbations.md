---
type: Document Section
title: Ensemble Forecasting With Control Forecast and Perturbations
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=ensemble-forecasting-with-control-forecast-and-perturbations
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=484,485
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00816
slug: ensemble-forecasting-with-control-forecast-and-perturbations
outline_level: 4
outline_order: 816
section_number: null
section_path:
- 10. Situational Awareness and Forecasting
- 10.5 Weather Forecasting
- 10.5.1 Existing Modeling Approach
- Ensemble Forecasting With Control Forecast and Perturbations
page_number: 484
page_numbers:
- 484
- 485
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: 6849608dfd20e891a08ab35dad1da0b810763b5f7cf3557c44ab9cbb0017977a
child_count: 0
---

# Ensemble Forecasting With Control Forecast and Perturbations

## Evidence

<!-- okf-trial:evidence-start -->
Two control or deterministic models are initialized using the GFS and ECMWF 
deterministic outputs.  An ensemble of nine members is also generated using an 
intelligent sub-selection of the NOAA GEFS saving considerable computing and 
financial resources.  The GEFS is a stochastically perturbed 30-member ensemble 
based on the GFS.  The ensemble members utilize the GFS analysis perturbed by a 6 h 
Ensemble Kalman Filter forecast ensemble.  Model uncertainty is introduced using the 
Stochastically Perturbed Physics Tendencies and Stochastic Kinetic Energy 
Backscatter schemes.  The computational cost would be prohibitive if we were to 
initialize a high-resolution WRF forecast corresponding to each GEFS member 
individually.  We therefore tested a novel forecast strategy using nine representative 
GEFS members that are dynamically selected to maintain the large-scale flow diversity 
of the entire GEFS ensemble.  The intended outcome is a WRF ensemble that is more 
accurate than a single WRF forecast at a higher resolution, yet also that provides 
meaningful information about forecast uncertainty at a drastically reduced cost.  This 
selection strategy involves analyzing the GEFS forecast 500 Hectopascals geopotential 
height field (Z500) for each GEFS members.  Selecting GEFS members to downscale 
consists of two steps intended to sample the mean and diversity of the ensemble.  The 
first step involves a Self-Organizing Map (SOM), which is an artificial neural network 
(AI) used as a clustering method to group together events with similar structure.  The 
SOM analysis is used to classify the GEFS ensemble into five nodes.  Overall, we 
selected the nine GEFS members that captured both the mean and outlier behavior of 
the large-scale flow in the full ensemble and use these distinct members from the 00Z 
and 12Z GEFS packages to downscale.  Thus, each forecast update utilized different 
ensemble members as determined by this methodology.

-454-

Model Outputs Including, for Example:
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [10.5.1 Existing Modeling Approach](../10-5-1-existing-modeling-approach.md)
* Previous topic: [Data Assimilation From Environmental Monitoring Systems Within the Electrical Corporation Service Territory](data-assimilation-from-environmental-monitoring-systems-within-the-elect.md)
* Next topic: [Model Outputs Including, for Example:](model-outputs-including-for-example.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 484-485.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 484-485.

---
type: Document Section
title: Model Overview
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=model-overview
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=482,483,484
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00814
slug: model-overview
outline_level: 4
outline_order: 814
section_number: null
section_path:
- 10. Situational Awareness and Forecasting
- 10.5 Weather Forecasting
- 10.5.1 Existing Modeling Approach
- Model Overview
page_number: 482
page_numbers:
- 482
- 483
- 484
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: f5f5ad0e4f90b07db96592257144d5fb66cbad1e5cf42f50c10a1be0f8d1e94f
child_count: 0
---

# Model Overview

## Evidence

<!-- okf-trial:evidence-start -->
PG&E builds, operates, and maintains core models and datasets used to train machine 
learning models and forecast PSPS events.  This section provides details on these 
foundational datasets and models.

PG&E partners with two external experts and employs internal weather modeling 
experts to deploy and maintain PG&E’s high-resolution weather models.  In 2014 PG&E 
partnered with Weather Decision Technology—since acquired by DTN, a weather 
forecasting company formerly known as Telvent DTN, Data Transmission Network and 
Dataline—to deploy the first Version of PG&E’s Operational Mesoscale Modeling 
System (POMMS), which is based on the Weather Research and Forecast (WRF) 
Model.  A second external expert has also been engaged since 2014, Atmospheric Data 
Solutions (ADS), which was recently acquired by Technosylva.  ADS-Technosylva has 
extensive knowledge of California fire weather and numerical weather prediction using

-452-

WRF and they work extensively with Southern California Edison Company (SCE), 
San Diego Gas & Electric Company (SDG&E), and other utilities, as well as firefighting 
agencies across the world.

WRF is a mesoscale numerical weather prediction system designed for both 
atmospheric research and operational forecasting applications.  It features two 
dynamical cores, a data assimilation system, and a software architecture supporting 
parallel computation and system extensibility.  WRF is currently being used 
operationally at National Centers for Environmental Prediction (NCEP) and other 
national meteorological centers and in real-time forecasting configurations at 
laboratories, universities, utilities and hundreds of companies.

PG&E first deployed the high resolution in-house mesoscale forecast model, POMMS, 
in November of 2014, and PG&E continues to improve and build upon the model 
framework to generate short to medium-term weather, outage, and fire potential 
forecasts across PG&E’s service territory.  We are currently on Version 4.0 of the core 
model; Table PG&E-10.5-1 below shows the model evolution:

TABLE PG&E-10.5-1   
PG&E OPERATIONAL MESOSCALE MODELING SYSTEM DEVELOPMENT 81

POMMS 
Version

Year 
Implemented

WRF 
Version 
Key Features

1 
2014 
3.5.1 
Single 3 kilometer (km) grid using boundary conditions from a 
12 km WRF run.

2 
2018 
4.0.2 
Nested 3 km grid, Mellor-Yamada-Nakanishi-Niino (MYNN) 
surface layer scheme, Rapid Update Cycle (RUC) land 
surface model, 30-year reanalysis.

3 
2020 
4.1.2 
Nested 2 km grid, Noah-MP land surface model, 
stochastically perturbed ensemble, 30-year reanalysis.  See 
text and Table 2 for details.

4 
2024 
4.5.2 
Nested 2 km grid, irrigation triggered by crop-growing 
season, Global Ensemble Forecasting System 
(GEFS)-based ensemble, 30-year reanalysis.

POMMS is a high-resolution weather forecasting model that generates important fire 
weather parameters including wind speed, temperature, Relative Humidity (RH), and 
precipitation.  Outputs from POMMS are used as inputs to the Nelson DFM model, and 
LFM models developed by Technosylva to derive key fire danger indicators such as 
1 hr., 10 hr., 100 hr., 1,000 hr. DFM, and LFM for multiple plant species.

30+ year climatologies of the same outputs have been produced and maintained since 
2019 and provide the same horizontal and temporal resolution as well as model physics 
to the operational forecast model.  These climatologies are utilized with fire occurrence 
datasets and outage datasets to build machine learning FPI and outage-ignition models 
that are utilized for PSPS.

-453-

The current POMMS model configuration deployed is WRF model Version 4.5.2, which 
provides data at 2x2 km spatial and hourly temporal resolution.  A nested grid 
configuration of 18-, 6-, 2-, and 0.67-km (on demand) grids horizontal grids are utilized.  
Adaptive time stepping is used for computational efficiency and the model was 
configured to run in the Amazon Web Services (AWS) cloud across different AWS 
regions for redundancy.  The POMMS forecasts include two deterministic forecasts, as 
well as a 9-member ensemble dynamically selected from the Global Forecast System 
(GFS) ensemble suite.  One deterministic model is initialized using ¼° output from the 
NCEP – GFS model data, as well as 1/12° Sea Surface Temperature analyses.  The 
GFS, often referred to as the American Model, is operated and maintained by NOAA’s 
National Center for Environmental Prediction and is the United States’ flagship global 
model.  The second deterministic model is initialized with the European Center for 
Medium Range Weather Forecast (ECMWF) global model.

Data Assimilation From Environmental Monitoring Systems Within the Electrical 
Corporation Service Territory
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [10.5.1 Existing Modeling Approach](../10-5-1-existing-modeling-approach.md)
* Next topic: [Data Assimilation From Environmental Monitoring Systems Within the Electrical Corporation Service Territory](data-assimilation-from-environmental-monitoring-systems-within-the-elect.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 482-484.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 482-484.

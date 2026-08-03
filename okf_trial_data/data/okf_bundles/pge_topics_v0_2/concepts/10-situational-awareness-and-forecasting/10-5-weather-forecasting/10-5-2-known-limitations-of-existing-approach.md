---
type: Document Section
title: 10.5.2 Known Limitations of Existing Approach
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=10-5-2-known-limitations-of-existing-approach
tags:
- document-section
- corpus-pge
- level-3
status: stable
generated:
  by: process:okf-trial-topic-bundle-v1
  at: '2026-08-02T00:00:00Z'
sources:
- id: source-pdf
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=488
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00820
slug: 10-5-2-known-limitations-of-existing-approach
outline_level: 3
outline_order: 820
section_number: 10.5.2
section_path:
- 10. Situational Awareness and Forecasting
- 10.5 Weather Forecasting
- 10.5.2 Known Limitations of Existing Approach
page_number: 488
page_numbers:
- 488
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: fd2c13a47a27ded7486ba9a4c7cab59019121d72db2e682e1f51ecc4d7b77f8d
child_count: 1
---

# 10.5.2 Known Limitations of Existing Approach

## Evidence

<!-- okf-trial:evidence-start -->
The electrical corporation must describe any known limitations of its existing modeling 
approach resulting from assumptions, data availability, and computational resources.  
It must discuss the impact of these limitations on the modeling outputs.

Running high-resolution models and ensembles is computationally expensive to perform 
for a large service territory and requires a large amount of storage.

• 
Each day, we receive approximately 1.4 terabytes of weather forecast data from our 
high-resolution model.  This data is in addition to ingesting and processing 
additional external sources of model data from several sources (e.g., American, 
European, Canadian global models, American high-resolution models, Technosylva, 
etc.), and does not factor in our high resolution DFM and LFM models, or 
climatological datasets, which are also produced hourly at 2 x 2 km resolution.

• 
To cover our entire service territory, our 2 x 2 km domain consists of 396 grid cells 
along the west-east dimension and 480 along the north-south dimension, for a total 
amount equaling 190,080 (396 X 480) 2 x 2 km grid cells.

• 
There is a total of 24 high resolution simulations completed each day (four times per 
day for the GFS control run and two times per day for the ECM control run and 
nine members of the ensemble, which is also run 2 times per day).  Each simulation 
generates 190,080 data points (1 per grid cell) every hour out 129 hours available in 
the forecast.  Thus, for a single variable, like temperature, there are 
588,487,680 data points generated per day (190,080 grid cells X 24 runs/day X 
129 hours/run).  There are 15 variables output at the surface, and 51 vertical levels 
(z) with output as well.  Not counting output from the 51 vertical levels, there are 
approximately 9 billion data points output each day at the near surface alone.  If our 
model resolution increased from 2 x 2 km to 1 x 1 km, this would quadruple the 
output and increase costs by 620 percent per model run.  If we increased our 
existing model resolution to achieve the highest possible score from the 2023 
maturity survey, 100 meters, the output would increase by a factor of 400.

We are limited by computer costs, storage costs and financial costs to run more and 
more granular dynamic weather models that are physics-based.  As AI and machine 
learning matures in numerical weather prediction, we may be able to achieve higher 
resolution forecasts at a greater cost-efficiency.

Forecast Accuracy
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [10.5 Weather Forecasting](../10-5-weather-forecasting.md)
* Previous topic: [10.5.1 Existing Modeling Approach](10-5-1-existing-modeling-approach.md)
* Next topic: [10.5.3 Planned Improvements](10-5-3-planned-improvements.md)
* Child topic: [Forecast Accuracy](10-5-2-known-limitations-of-existing-approach/forecast-accuracy.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, page 488.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, page 488.

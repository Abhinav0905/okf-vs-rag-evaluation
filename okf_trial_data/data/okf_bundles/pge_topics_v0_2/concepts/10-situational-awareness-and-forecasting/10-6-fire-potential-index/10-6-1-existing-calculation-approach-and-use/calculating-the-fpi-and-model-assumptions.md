---
type: Document Section
title: Calculating the FPI and Model Assumptions
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=calculating-the-fpi-and-model-assumptions
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=496,497,498,499,500,501
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00840
slug: calculating-the-fpi-and-model-assumptions
outline_level: 4
outline_order: 840
section_number: null
section_path:
- 10. Situational Awareness and Forecasting
- 10.6 Fire Potential Index
- 10.6.1 Existing Calculation Approach and Use
- Calculating the FPI and Model Assumptions
page_number: 496
page_numbers:
- 496
- 497
- 498
- 499
- 500
- 501
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: 95cb74ab72551023604cc396ebdb300c88e8ec9d25f050cde9430f320c1102e2
child_count: 1
---

# Calculating the FPI and Model Assumptions

## Evidence

<!-- okf-trial:evidence-start -->
The FPI model is based on a multi-classification balanced random forest framework, a 
state-of-the-art open-source machine learning model based on decision trees.

FPI is trained on a novel fire occurrence dataset (McClure et. al., 2023) that combines 
agency fire information with satellite fire detections.  Fire detections are derived from 
satellite infrared data and provide information on the location, intensity and time of fires.  
FPI v5.0 was trained on satellite fire detections using defined classes that separate 
small, moderate, critical, and catastrophic defined fires.  These classes are determined 
by both fire spread and intensity.  For example, a slow moving, low intensity fire would 
be defined as small, while a fast moving, intense fire would be defined as catastrophic.  
Historical fire information, such as impacts and consequences, were used to define 
these classes.

The class breakpoints are shown in the table below based on if the detect interval was 
less than or greater than 3 hours.  Note that the class names pertain to the FPI 
definition only and should not be confused with the Office of Energy Infrastructure 
Safety definition of Catastrophic Fire.

Table PG&E-10.6.1-1 below summarizes our FPI Class Breakpoints.

176 McClure et al., Consistent, high-accuracy mapping of daily and sub-daily wildfire growth 
with satellite observations, International Journal of Wildland Fire (Apr. 3, 2023), available at:  
https://www.publish.csiro.au/wf/fulltext/WF22048.

-466-

TABLE PG&E-10.6.1-1:   
FPI CLASS BREAKPOINTS 83

VIIRS Growth (Acres), Fire 
Radiative Power (Megawatts (MW))

VIIRS Growth, Fire Radiative Power

(MW) 
(>=3 Hours Between VIIRS Detects)

FPI Class

(<3 Hours Between VIIRS Detects)

Small 
<70 acres 
<70 acres

Large 
<200 acres OR <200 MW 
<200 acres OR <200 MW

Critical 
<2,000 acres OR <2,000 MW 
<7,000 acres OR <7,000 MW

Catastrophic 
>=2,000 acres & >=2,000 MW 
>=7,000 acres & >=7,000 MW

The fire occurrence data is sampled from polar-orbiting satellites that scan the surface 
of Earth in a whisk-broom manner along swaths.  We found two modes of detection 
between scans due to the lag time between VIIRS instruments on satellites Suomi-NPP 
and NOAA-20, as well as limb and nadir detections.  Thus, to utilize the most fire 
occurrence data, we classify two sets of breakpoints based on time between detections 
with final values being derived via a grid search.  Essentially, high intensity and fast 
spreading fires are classified as catastrophic for FPI training purposes.

Fire intensity provided in MW is related to the satellite detected fire radiative power 
which is an additional observed dimension to acres burned to understand fire dynamics.  
Analyzing fire radiative power of historical fires, we find fires with higher fire radiative 
power are more likely to escape containment and result in building losses.

Table PG&E-10.6.1-2 below presents how consequences from historic fires are 
distributed in these four classes across the lifespan from initiation, the first 24 hours and 
through the extended burning period.  Most building losses occur in the first 24 hours in 
the catastrophic class, with very few losses occurring in the moderate and small 
classes.

-467-

TABLE PG&E-10.6.1-2:   
FIRE CONSEQUENCE DISTRIBUTION BY CLASS BREAKPOINTS 84

% of Total Buildings Damaged 
Buildings Damaged per 10,000 Acres

FPI Class Actual 
Small 
Large 
Critical 
Catastrophic 
Small 
Moderate 
Critical 
Catastrophic

Initial Detect 
0.0% 
0.8% 
4.6% 
30.8% 
2 
6 
78 
683

Initial Burning Period 
(0+ to 24+ hours)

0.0% 
1.2% 
3.7% 
31.1% 
– 
19 
36 
392

Second Burning 
Period (24+ to 72+ 
hours)

0.0% 
0.0% 
3.4% 
8.0% 
– 
1 
26 
69

Third Burning Period 
(3+ to 7+ days)

0.0% 
0.2% 
4.4% 
2.6% 
– 
3 
19 
29

Extended Burning 
Period 
(More than 7+ days)

0.0% 
0.0% 
1.0% 
8.2% 
– 
– 
2 
34

The FPI model increased from a 3-class to a 4-class model with the addition of a new 
Critical fire class.  The Catastrophic fire class focuses more on wind driven fires, and 
the new Critical fire class focuses more on fuel and terrain driven fires.

The mean final fire size of those fires with a first detect with these classifications are as 
follows:

• 
Small:  approximately 300 acres;

• 
Large:  approximately 1,500 acres;

• 
Critical: 20,000 acres; and

• 
Catastrophic ~80,000 acres.

The FPI model is output hourly for each 0.7km2 hexagon with features of hourly weather 
and fuel moisture, fuel types and terrain as input.

𝑃𝑃(𝐹𝐹𝑃𝑃𝐹𝐹𝑙𝑙𝑙𝑙𝑎𝑎𝑎𝑎𝑎𝑎,ℎ𝑎𝑎𝑒𝑒𝑎𝑎𝑤𝑤𝑙𝑙𝑖𝑖,ℎ𝑙𝑙𝑜𝑜𝑁𝑁) = 𝑓𝑓(𝑓𝑓𝐿𝐿𝑦𝑦𝑐𝑐𝑐𝑐𝑐𝑐𝐿𝐿𝑐𝑐ℎ𝑎𝑎𝑒𝑒𝑎𝑎𝑤𝑤𝑙𝑙𝑖𝑖,ℎ𝑙𝑙𝑜𝑜𝑁𝑁)

PG&E tested over 160 features in an iterative process to train the FPI5.0.  PG&E used 
model skill, feature exploratory and correlation analysis and machine learning 
interpretability tools including various feature importances and shapely additive 
explanations to select the final model features for operations.  More than 
70 formulations of FPI were trained and evaluated in an iterative process to optimize 
model skill, model interpretability, explainability and operability.

The FPI model improved the spatial relations of weather, fuel moisture, fuels, and 
terrain model data with fire data by using VIIRS Satellite Fire Detection polygon shapes.

-468-

Further, the temporal relations of fire growth and model data are also improved by using 
GOES satellite fire detection hourly derived growth between VIIRS detects.  The FPI 5.0 
model shows improved skill across all fire classes compared to the previous FPI 4.0 
model.  Table PG&E-10.6.1-3 below summarizes our FPI model skill score comparison.

TABLE PG&E-10.6.1-3:   
FPI MODEL SKILL SCORE COMPARISON 85

FPI 4.0 Model 
Receiver-Operating 
Characteristic Curve 
(ROC) Area Under the

FPI 5.0 Model

Fire Class

Curve (AUC)

ROC AUC

Catastrophic 
0.88 
0.95

Critical 
Class Not Used 
0.88

Large 
0.55 
0.62

Small 
0.68 
0.73

Macro-Average ROC AUC 
0.70 
0.83

32 features were selected in the final FPI model for operations, which are summarized 
and presented in the figures and tables below.  The FPI 5.0 model features include:

• 
Weather features of wind speed, turbulence, temperature, and vapor pressure 
deficit;

• 
New Normalized Difference Vegetation Index herbaceous fuel moisture model and 
enhanced existing dead, herbaceous and woody fuel moisture models;

• 
Topography features including terrain ruggedness and slope;

• 
New soil moisture and solar radiation features;

• 
Improved fuel categories;

• 
New fuel properties features including fuel bed depth and fuel complexity; and

• 
The fuel categories, fuel properties and topography features are aggregated to the 
0.7 km2 hexagons from the underlying 30 m resolution.

Table 10-5 below summarizes FPI model features.

-469-

TABLE 10-5:   
FIRE POTENTIAL INDEX MODEL FEATURES 86

Feature Group/

Feature 
(Predictor) 
Altitude 
Description 
Source

Update 
Cadence

Spatial 
Granularity

Temporal 
Granularity

TerrainRugged_Mean 
surface 
Measure of terrain ruggedness in each h3 hexagon 
DEM 
N/A 
10m 
N/A

Slope_Degree_Mean 
surface 
Measure of slope in each h3 hexagon 
DEM 
N/A 
10m 
N/A

Fuels:  Grass 
300 m 
Proportion of fuel category in h3 hexagon cell attributed 
to grass 
Technosylva 
Annual 
30m 
N/A

Proportion of fuel category in h3 hexagon cell attributed 
to grass shrub 
Technosylva 
Annual 
30m 
N/A

Fuels:  Grass Shrub 
surface

Proportion of fuel category in h3 hexagon cell attributed 
to shrub 
Technosylva 
Annual 
30m 
N/A

Fuels:  Shrub 
surface

Proportion of fuel category in h3 hexagon cell attributed 
to timber litter 
Technosylva 
Annual 
30m 
N/A

Fuels:  Timber Litter 
surface

Fuels:  Timber 
Understory 
surface

Proportion of fuel category in h3 hexagon cell attributed 
to timber understory 
Technosylva 
Annual 
30m 
N/A

-470-

Fuels:  Urban Roads 
Agg Low Burnable 
surface

Proportion of fuel category in h3 hexagon cell attributed 
to dense urban, roads, or agriculture land 
Technosylva 
Annual 
30m 
N/A

Proportion of fuel category in h3 hexagon cell attributed 
to urban, roads, or agriculture land adjacent or 
surrounded by burnable fuels 
Technosylva 
Annual 
30m 
N/A

Fuels: Urban Roads 
Agg High Burnable 
surface

fuel_bed_depth_ft 
surface 
The fuel bed depth from fuel model classes 
Technosylva 
Annual 
30m 
N/A

The average fuel complexity derived from fuel model 
data 
Technosylva 
Annual 
30m 
N/A

ave_fuel_complexity 
surface

The moisture content in the 1,000 hr. dead fuel model 
class

POMMS & 
Technosylva 
2x per day 
2km 
hourly

dfm_1000hr 
surface

The moisture content in the 100 hr. dead fuel model 
class

POMMS & 
Technosylva 
2x per day 
2km 
hourly

dfm_100hr 
surface

The moisture content in the 10 hr. dead fuel model 
class

POMMS & 
Technosylva 
2x per day 
2km 
hourly

dfm_10hr 
surface

TABLE 10-5:   
FIRE POTENTIAL INDEX MODEL FEATURES

(CONTINUED)

Feature Group/

Feature 
(Predictor) 
Altitude 
Description 
Source

Update 
Cadence

Spatial 
Granularity

Temporal 
Granularity

POMMS & 
Technosylva 
2x per day 
2km 
hourly

dfm_1hr 
surface 
The moisture content in the 1 hr. dead fuel model class

The moisture content in the LFM chamise new growth 
class

POMMS & 
Technosylva 
daily 
2km 
daily

lfm_chamise_new 
surface

POMMS & 
Technosylva 
Daily 
2km 
daily

ndvi 
surface 
The Normalized Vegetation Index per h3 hexagon

smois_0 
 5 cm 
Moisture content in the soil at a depth of 5 cm 
POMMS 
2x per day 
2km 
hourly

vpd_mb_300m 
300m 
Vapor pressure deficit at 300m 
POMMS 
2x per day 
2km 
hourly

vpd_mb_50m 
50m 
Vapor pressure deficit at 50m 
POMMS 
2x per day 
2km 
hourly

vpd2m_mb 
2m 
Vapor pressure deficit at 2m 
POMMS 
2x per day 
2km 
hourly

-471-

sfcdownshortwaveflux 
surface 
Shortwave flux at the surface – solar radiation 
POMMS 
2x per day 
2km 
hourly

temp_f_300m 
300m 
Temperature at 300m above surface in Fahrenheit 
POMMS 
2x per day 
2km 
hourly

temp_f_50m 
50m 
Temperature at 50m above surface in Fahrenheit 
POMMS 
2x per day 
2km 
hourly

temp2m_f 
2m 
Temperature at 2m above surface in Fahrenheit 
POMMS 
2x per day 
2km 
hourly

tke_pbl_300m 
300m 
Kinetic energy per unit mass observed in eddies 
characteristic of turbulent flow in Joules/kg at 300m 
POMMS 
2x per day 
2km 
hourly

tke_pbl_50m 
50m 
Kinetic energy per unit mass observed in eddies 
characteristic of turbulent flow in Joules/kg at 50m 
POMMS 
2x per day 
2km 
hourly

ustar_frc_vel 
2m 
Wind shear stress in velocity terms. 
POMMS 
2x per day 
2km 
hourly

ws_mph_300m 
300m 
Wind speed at 300m above surface 
POMMS 
2x per day 
2km 
hourly

ws_mph_50m 
50m 
Wind speed at 50m above surface 
POMMS 
2x per day 
2km 
hourly

ws_mph 
10m 
Wind speed at 10m above surface 
POMMS 
2x per day 
2km 
hourly
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [10.6.1 Existing Calculation Approach and Use](../10-6-1-existing-calculation-approach-and-use.md)
* Previous topic: [Summary](summary.md)
* Child topic: [How We Use the FPI in Operations:](calculating-the-fpi-and-model-assumptions/how-we-use-the-fpi-in-operations.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 496-501.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 496-501.

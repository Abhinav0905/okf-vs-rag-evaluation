---
type: Document Section
title: Mitigations
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=mitigations
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=491,492
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00831
slug: mitigations
outline_level: 4
outline_order: 831
section_number: null
section_path:
- 10. Situational Awareness and Forecasting
- 10.5 Weather Forecasting
- 10.5.5 Weather Station Maintenance and Calibration
- Mitigations
page_number: 491
page_numbers:
- 491
- 492
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: 7aed06d5827ad25f28eca1fc1df53dc455700dff27e0f72b78962acd8d35dfe2
child_count: 0
---

# Mitigations

## Evidence

<!-- okf-trial:evidence-start -->
If any station goes beyond 15 months since its last calibration due to any reason, the 
station is considered out of compliance with PG&E's internal calibration guidelines and 
is blacklisted by PG&E meteorology by marking the station as “untrusted” in internal 
databases.  An untrusted status removes the weather station and live data from 
situational awareness systems involved in PSPS until calibration or maintenance is 
completed and the station can be toggled back to “trusted” status.  Weather station 
parts/components can and will fail outside routine maintenance cycles, and we have a 
process to identify, assign, track and perform emergent maintenance.  Our external 
vendor collects data from each station every 10 minutes and processes it through a 
system of automated data and station health checks (e.g., battery voltage, range, and 
reasonableness checks).  Alerts are generated for any anomalies and are verified by an 
external analyst.  After verification, these alerts are sent to our Enterprise Network 
Operations Center, where an internal incident ticket is generated and assigned to the 
local telecom yard and technician for resolution.  These trouble tickets are typically 
generated due to low or dead batteries, inconsistent or dead modems/comms, bad/dead 
datalogger, or suspect data.  In some cases, we find stations vandalized 
(e.g., gunshots).  In the case of suspect data, we blacklist the station by marking the 
station as “untrusted” in internal databases until sensors have been replaced.

-461-

Acceptable Percentage of Weather Station Outages
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [10.5.5 Weather Station Maintenance and Calibration](../10-5-5-weather-station-maintenance-and-calibration.md)
* Previous topic: [Routine Calibration After Installation](routine-calibration-after-installation.md)
* Next topic: [Acceptable Percentage of Weather Station Outages](acceptable-percentage-of-weather-station-outages.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 491-492.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 491-492.

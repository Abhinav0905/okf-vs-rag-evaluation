---
type: Document Section
title: Protective Equipment and Settings on Distribution Lines
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=protective-equipment-and-settings-on-distribution-lines
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=356,357
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00563
slug: protective-equipment-and-settings-on-distribution-lines
outline_level: 5
outline_order: 563
section_number: null
section_path:
- 8. Grid Design, Operations, and Maintenance
- 8.7 Grid Operations and Procedures
- 8.7.1 Equipment Settings to Reduce Wildfire Risk
- 8.7.1.1 Protective Equipment and Device Settings
- Protective Equipment and Settings on Distribution Lines
page_number: 356
page_numbers:
- 356
- 357
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: bafa11523a9fc2db365dd8ba32a5e5facd0aead40a50271f3094657380cad9a4
child_count: 0
---

# Protective Equipment and Settings on Distribution Lines

## Evidence

<!-- okf-trial:evidence-start -->
Distribution circuits enabled with EPSS are configured to trip-bolted fault conditions at 
100 milliseconds or less.  EPSS settings also allow circuit breakers and reclosers to 
clear faults beyond fuses.  This allows clearance of all fuse-protected circuit segments 
with ganged-three phase interruption to prevent back-feed into the fault.

Historically, the majority of ignitions that have occurred while EPSS protection is 
enabled have been the result of high impedance, low amperage fault conditions that 
were not detectable by traditional EPSS settings.  DCD technology can improve the 
ability to detect and isolate high impedance faults before an ignition can occur.  This 
technology and the algorithms associated with it are hardware vendor specific, but are 
commonly referred to as DCD for the purpose of this narrative.  The engineering and

-326-

programming of existing equipment capable of DCD and the installation of new 
equipment with DCD functionality helps to address high impedance fault conditions 
within the HFRA.  To address fault types not yet fully mitigated through the EPSS 
program, we began deployment of DCD in 2022 to supplement and provide enhanced 
ground fault protection to address low-current, high-impedance faults.  Through 2024, 
DCD has been installed on 1,983 protection devices, providing enhanced protection 
across 87 percent of the HFTD/HFRA.

The GM-06 (DCD) commitment from the 2023-2025 WMP will conclude in 2025.  DCD 
will continue as part of regular operational activities.

Additionally, when EPSS is enabled on three-wire distribution systems, SGF settings 
are implemented to help detect lower current fault conditions.  This protection was 
generally set to identify 15 amperage faults within 15 seconds and de-energize the 
conductor to protect the line.  In 2023, there were observed ignitions that occurred 
during EPSS protection that were lower than the detectable thresholds of DCD.  It was 
identified that a lower SGF pickup could have interrupted the events sooner, potentially 
preventing the ignition (DCD not present).  In 2024, we revised SGF trip floor settings 
criteria and device reprogramming planned for increased detection of high-impedance 
faults to 5 amperage faults within 5 seconds.

To further support our identification and response to high impedance faults, we have 
implemented new data-driven capabilities leveraging our SmartMeter network.  PV 
Alerts work for the 3-wire distribution system with Line-to-Line connected transformers.  
PV Alert indicates low SmartMeter Voltage (25 – 75 percent of nominal 240V).  Network 
Interface Card (NIC) remains on and able to return pings down to 25 percent Voltage, 
while metrology turns off at 75 percent voltage.  New PV alert configuration settings 
prevent nuisance alerts from transient conditions.  PG&E has also enabled single-phase 
and polyphase SmartMeter devices to send real-time alarms to the Distribution 
Management System when they detect partial voltage conditions.

A partial voltage condition is one where two or more SmartMeter devices indicate that 
the voltage passing through them has dropped, triggering an alarm at the Control 
Center.  When wildfire conditions are elevated, the Control Center has the discretion to 
de-energize the circuit utilizing the existing SCADA capabilities.  The partial voltage 
alarm indicates that there may be a low-current fault on the line.  This capability helps 
PG&E detect and locate a downed wire within minutes, instead of relying on an 
employee assessment or customer alert.  This can reduce the amount of time a downed 
line is energized and capable of potentially causing an ignition.  A total of 86 partial 
voltage force outs were performed between 2022-2024, largely triggered by vegetation 
or animal contact.
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [8.7.1.1 Protective Equipment and Device Settings](../8-7-1-1-protective-equipment-and-device-settings.md)
* Previous topic: [Settings Used to Reduce Wildfire Risk](settings-used-to-reduce-wildfire-risk.md)
* Next topic: [Protective Equipment and Settings on Transmission Lines](protective-equipment-and-settings-on-transmission-lines.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 356-357.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 356-357.

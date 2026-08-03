---
type: Document Section
title: 12.2 Summary of Enterprise Systems
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=12-2-summary-of-enterprise-systems
tags:
- document-section
- corpus-pge
- level-2
status: stable
generated:
  by: process:okf-trial-topic-bundle-v1
  at: '2026-08-02T00:00:00Z'
sources:
- id: source-pdf
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=569,570,571,572,573,574
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00918
slug: 12-2-summary-of-enterprise-systems
outline_level: 2
outline_order: 918
section_number: '12.2'
section_path:
- 12. Enterprise Systems
- 12.2 Summary of Enterprise Systems
page_number: 569
page_numbers:
- 569
- 570
- 571
- 572
- 573
- 574
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: 2835437710d0ddfd83d1b1ef5e904b79949ce03c552f875b1070efa2d5357229
child_count: 0
---

# 12.2 Summary of Enterprise Systems

## Evidence

<!-- okf-trial:evidence-start -->
Electrical corporations must provide a summary narrative of no more than three pages 
that discusses how its enterprise systems contain, account, or allow for the following:

• 
Any database(s) the electrical corporation used for data storage;

• 
Internal procedures for updating the enterprise system, including database(s), any 
planned updates, and the ability to migrate data across systems and ensure 
accuracy if necessary;

• 
The electrical corporation’s asset identification process;

• 
The electrical corporation’s process for integrating 100 percent asset identification 
or its justification if not currently in place;

• 
Processes to ensure data integrity (accuracy, completeness, and quality of data), 
accessibility (ability of the electrical corporation to access data across formats and 
locations), and retention (any policies the electrical corporation for how long it stores 
data and how it disposes of data after any retention period);

• 
Any Quality Assurance (QA)/Quality Control (QC) or auditing of its system;

• 
Overview of any data governance plan that the electrical corporation has in place.  
Highlighting any data stewardship practices;

• 
How current WMP initiatives and activities are being tracked and monitored in 
enterprise systems;

• 
Employee and/or contractor ability to access and interact with the data and systems 
for tracking work order status and scheduling;

• 
How the electrical corporation’s work order and asset management systems feed 
into risk analysis and alternative or interim activity selection; and

• 
Any changes to the electrical corporation’s enterprise systems since the last Base 
WMP submission and a brief explanation as to why those changes were made.  
Include any planned improvements or updates to the enterprise systems and the 
timeline for implementation.

In this section we provide a summary of Enterprise Systems.

• 
Databases:  PG&E uses several databases or data platforms designed to handle 
diverse data requirements of PG&E’s wildfire mitigation technology.  Key databases 
primarily supporting wildfire mitigation technology include: Geospatial, Telemetry, 
Asset Management, Incident Management, Customer Information, and Data 
Analytics Platform.  For example: Each asset in the asset registry must have an 
established system of entry.  The preferred systems of entry are Electric GISs, 
specifically Electric Transmission Geographic Information System and Electric

-539-

Distribution Geographic Information System.  Additionally, these systems capture 
and record the spatial location and electrical connectivity of the assets.

• 
Internal Procedures:  PG&E has an Information Technology (IT) Management of 
Change (MOC) procedure.  It is a structured approach to make changes or updates 
to the enterprise systems.  This procedure specifies that changes or updates are 
planned, assessed for potential impacts, tested, and coordinated with relevant 
stakeholders.  The primary goal of the MOC procedure is to obtain the necessary 
approvals while minimizing the risk to production enterprise systems and business 
processes.  The approach to data migration is tailored to each project, adjusting to 
the varying levels of complexity involved.  For example, in the One VM system, the 
data migration framework and strategy are designed to understand and identify the 
data migration scope, undertake data cleansing, data transformation, and data 
mapping activities.  It also includes steps for data validation and data quality 
assessment, followed by data migration to the production environment.

• 
Asset Identification Process:  In accordance with International Organization for 
Standardization (ISO) 55001 international asset management standards, PG&E 
asset management system standards241 require the risk, performance and cost of 
electric operations assets and the supporting information systems to be managed.  
The assets under management are defined by the standards and require that the 
inventory and critical attributes of those assets be managed in electric Asset 
Registry systems (e.g., GIS, SAP).  As new asset types are identified and put into 
service, those assets are also required to be added to the Asset Registry systems.  
As part of our electric asset data management program, which is certified under 
ISO 55001, PG&E has developed standards, programs, processes and controls to 
ensure the integrity of its electric asset data.  Foundational to this program is the 
Asset Registry Data Management Standard, which outlines required practices 
spanning the data lifecycle from the ingestion of newly created asset records to the 
remediation of historic data records to record retirement.

Electric asset identification is enabled through execution of programs consistent 
with this standard, including:

1) As-Built Program:  This program enables systematic ingestion into our Asset 
Registry database (GIS) of traceable, verifiable, accurate and complete data for 
all newly constructed assets and assigns unique identifiers for each asset.  The 
As-Built Program consults with Asset Management to identify assets for which 
attributes must be collected, reported and updated in the Asset Registry.  
Assets are selected based on whether they require inspection, maintenance or 
are involved in risk modeling.

2) Data Remediation Programs: PG&E also identifies assets through programs 
designed to improve the accuracy of its asset data.  The Map Correction 
program partners with frontline workers (e.g., inspectors) to leverage 
field-based observations to correct legacy inaccuracies in asset-related data, 
including identification of in-field assets that are missing from the Asset

241 The supporting documents are available at:  PG&E’s Community Wildfire Safety Program.

-540-

Registry.  The Data Remediation program develops projects that target specific 
data gaps/inaccuracies through field or desktop research, records research or 
applied analytics.  These projects may also include deployment of new 
technologies, procedures or processes needed to remediate the root cause 
data quality issues and avoid recurrence.

• 
Total Asset Integration:  PG&E interprets OEIS guidance as referring to the process 
or programs used to integrate critical asset-related datasets.  Since 2020, PG&E 
has been systematically integrating and providing access to its most critical electric 
asset and wildfire related data in our Enterprise analytics platform – Palantir 
Foundry.242  This program enhances our ability to make risk-informed, data-driven 
decisions for critical wildfire related programs such as PSPS, EPSS, and asset risk 
quantification.  As part of this program, PG&E has integrated physical asset, 
operational, lifecycle, and environmental data from over 50 existing disparate, 
purpose-built data systems into Palantir Foundry.  PG&E’s recent focus has been 
integrating Asset Registry data with asset condition and asset operating history data 
for risk-prioritized asset types.  The data integration work provides enterprise-wide 
access to reusable, high-quality, governed and integrated electric asset data.  
These foundational datasets are then used to build analytic tools that support a 
variety of analyses and applications, including situational awareness, asset health 
assessment, wildfire risk mitigation programs and WMP regulatory reporting 
(e.g., OEIS Spatial Quarterly Data Reporting).  PG&E’s asset data is also integrated 
through core system-to-system integrations (e.g., GIS to SAP integrations) where 
Asset Registry information from GIS is needed in other systems to manage 
workflows.  A program has been implemented to monitor the fidelity of the electric 
asset data integration between GIS to SAP.

• 
Data Integrity:  The Enterprise Data Management Policy (GOV-09)243 formalized 
PG&E’s goal of effectively and accurately managing data as an asset by 
implementing and maintaining an Enterprise Data Management Program.  
Functional Areas operationalize programs to conform with these policies addressing 
integrity, accessibility, and retention as exemplified by the Electric Asset 
Management program portfolio detailed above in Total Asset Integration.  PG&E 
also established metrics for electric data asset management to measure data 
management maturity and the quality of critical data assets.  These metrics are 
calculated using sub metrics measuring the extent to which:  (1) critical data has 
been identified; (2) ownership for critical data has been identified; (3) data quality 
rules for critical data have been identified; and (4) critical data aligns to data quality 
rules.  This helps to ensure that PG&E has practices in place that enable good 
quality data and that the data quality is, in fact, good.  The metrics also look at a 
broader, company-wide level of tracking critical data under management.  This is 
tracked in a tactical year-by-year perspective, but also an overall goal perspective.  
Data remediations at the tactical level are also being tracked to show how data 
quality is being improved.

242 For more Information, see Palantir’s website, available at:  
https://www.palantir.com/platforms/foundry/. 
243 The supporting document is available at:  PG&E’s Community Wildfire Safety Program.

-541-

• 
System QA/QC:  PG&E Test Center of Excellence has established test processes, 
procedures, standards, and guidelines.  PG&E has an IT MOC procedure which 
ensures that application teams are responsible for testing changes before 
scheduling them in production enterprise systems.

• 
Data Governance Plan:  See Data Integrity above.

• 
WMP Initiative Tracking:  PG&E’s WMP initiatives are tracked and monitored in 
Palantir Foundry and Excel.

• 
Employee/Contract System Access:  MyElectronicAccess (MEA)244 is PG&E’s 
enterprise-standard identity governance and administration system.  It is used by 
PG&E employee and contractors to submit and track access requests to PG&E data 
applications and systems.  MEA also provides capabilities to approve access 
requests, perform access reviews, and manage MEA governed roles and 
entitlements.  Additionally, MEA provides reporting capabilities to support business, 
compliance, and auditing processes.

• 
Work and Asset Management System Feed Into Risk Model:  PG&E’s wildfire risk 
model is made up of the Ignition Consequence model and the Ignition Probability 
model.  The Ignition Consequence model is constructed from annually generated 
weather and fire behavior analysis datasets.  The Ignition Probability models, 
depending on the subset, are built using annually generated datasets for weather, 
vegetation, equipment failures, equipment geo-location, and other characteristic 
values.  These datasets come from PG&E’s work order and asset management 
systems.  Provenance information, including its original source and generation 
date(s), is documented for each dataset used for building a WDRM version release.  
The provenance information is included in the WDRM Version documentation and is 
also published with its online implementation for end-users in Palantir Foundry.  The 
Wildfire Risk Models provide the different level of risk mitigation effectiveness at the 
program level for alternative solutions that are considered.  In addition, the risk 
model takes into account the cost to implement.  This functionality then allows the 
user to compare cost benefit ratio across mitigation alternatives.  This allows a user 
to make informed mitigation alternative tradeoffs.

• 
Changes to Enterprise Systems:  Multiple system enhancements have been 
implemented since the last WMP submission.  VM enhancements include updates 
to improve data quality, document reasons for removal, and improved program 
record keeping.  Continued investments in PG&E’s wildfire technology over the 
2026-2028 WMP will focus on enabling business capabilities in several key 
programs in the Data, Analytics & Insights, Event Management, Engineering & 
Work Management, System Planning & Asset Management, Customer Experience 
& Insights value streams, as well as in areas that may require delivery of technology 
solutions where additional research is required, that will drive more informed risk 
analysis and more agile and real-time PSPS scoping capabilities.

244 The supporting document is available at:  PG&E’s Community Wildfire Safety Program.

-542-

PACIFIC GAS AND ELECTRIC COMPANY

2026-2028 WILDFIRE MITIGATION PLAN

SECTION 13

LESSONS LEARNED

-543-

13. Lessons Learned
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [12. Enterprise Systems](../12-enterprise-systems.md)
* Previous topic: [12.1 Targets](12-1-targets.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 569-574.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 569-574.

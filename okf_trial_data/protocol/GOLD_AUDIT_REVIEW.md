# Independent semantic review of `wmp_okf_pge_97_v1`

Date: 2026-08-02  
Benchmark SHA-256: `1ea5c2142565d4bde6a5b0395887528295bc1434a65780e7678529ccd8ee3971`  
Source PDF SHA-256: `e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a`

## Decision

Do not use the current benchmark for paid judging. The deterministic audit confirms that all 83 answerable items point to page numbers present in the corpus, but its zero-flag result does not establish semantic validity. It measures lexical support over the union of all expected pages and therefore cannot detect an irrelevant expected page, a reversed causal relationship, or a reference answer that contradicts the source.

The defects are concentrated in the harmonized multi-page items. Four artificial combinations should preferably be removed (`wmp_q36`, `wmp_q38`, `wmp_q42`, and `wmp_q48`), although exact fact-only rewrites are supplied below if preserving question count is important. The other defective items should be corrected before the benchmark is versioned again. `NEG-004` also needs a page/reference correction. The 14 true unanswerable controls remain valid.

This is a single-reviewer semantic audit. A second independent reviewer should approve the revised benchmark before the confirmatory run.

## Remove rather than repair

### `wmp_q36`

- Problem: page 13 merely lists California Community Colleges in the table of contents (`PGE-00011`); page 37 describes an adaptive strategy and community partnerships generally (`PGE-00040`). The source never connects the college partnership to PG&E's adaptive learning strategy. The reference answer labels this speculation as a document-supported relationship.
- Action: remove. Rewriting it as two unrelated factual subquestions would no longer test the claimed connection.
- If count preservation is required, use expected pages `[13, 37]` and this explicitly conjunctive rewrite: "What does PG&E say about keeping its wildfire-mitigation strategy adaptive, and which California Community Colleges partnership subsections are listed in the WMP table of contents?"
- Count-preserving reference: "Page 37 says PG&E remains committed to continuously assessing evolving threats, learning from events within and beyond its territory, and maintaining a proactive, adaptive approach. Separately, the table of contents lists California Community Colleges sections for Overview (9.8.2.1), Partnership History (9.8.2.2), and Future Projects (9.8.2.3). The cited passages do not state that the college partnership is the mechanism for the adaptive strategy."

### `wmp_q38`

- Problem: page 379 describes qualifications for Troublemen and Distribution Line Technicians (`PGE-00396`); page 431 describes RCD grants (`PGE-00457`); page 340 describes generic asset-work-order requirements (`PGE-00354`, `PGE-00355`). Nothing says these workers monitor or reinspect RCD-funded vegetation projects. The reference invents that operational link.
- Action: remove.
- If count preservation is required, use expected pages `[379, 431]` and this explicitly conjunctive rewrite: "What qualifications does the WMP list for Troublemen in risk-event inspection, and what does it report about the El Dorado and Nevada County Resource Conservation District grants?"
- Count-preserving reference: "Troublemen must be Qualified Electrical Workers (QEW); the table lists no wildfire- or PSPS-specific certification beyond QEW and says their work supports safe equipment operation. Separately, PG&E reports a grant to El Dorado RCD to complement CAL FIRE funding for Spanish Flats and Traverse Creek, anticipated to treat 70 acres, and a Nevada County RCD grant for roadside brushing anticipated to treat two linear miles. The source does not say Troublemen monitor or reinspect those RCD projects."

### `wmp_q42`

- Problem: pages 187-188 present illustrative mechanics and explicitly say the values do not necessarily reflect commitments or WMP targets (`PGE-00188`, `PGE-00189`). Page 37 describes an adaptive strategy (`PGE-00040`), but the source does not say this example calculation feeds the adaptive process. Page 325 is unrelated switch-maintenance material (`PGE-00338`, `PGE-00339`). The same example is covered more cleanly by a corrected `wmp_q49`.
- Action: remove as an unsupported and duplicative causal synthesis.
- If count preservation is required, use expected pages `[37, 187, 188]` and this explicitly conjunctive rewrite: "What does PG&E's illustrative undergrounding/covered-conductor risk-reduction calculation show, what caveat accompanies its values, and how does PG&E separately characterize its adaptive wildfire strategy?"
- Count-preserving reference: "The illustrative calculation applies 98% effectiveness to 25 units of workplan WDRM risk exposure to produce 24.5 units of workplan wildfire-risk reduction. The preceding text says the values illustrate calculation mechanics, do not reflect specific commitments, and do not necessarily align with WMP targets. Separately, page 37 says PG&E continuously assesses evolving threats and maintains a proactive, adaptive approach. The WMP does not state that this example calculation feeds that adaptive process."

### `wmp_q48`

- Problem: page 68 documents the Dixie Fire tree contact and non-operating third fuse (`PGE-00068`). Page 354 is a past-due **substation** work-order table (`PGE-00368`), while page 446 covers vegetation work orders (`PGE-00471`). The source does not state that either backlog system would have prevented the fuse behavior in the Dixie Fire. The reference turns a plausible hypothesis into a source fact.
- Action: remove.
- If count preservation is required, use expected pages `[68, 354, 446]` and this explicitly conjunctive rewrite: "What does the WMP report about the cause of the Dixie Fire, and what do its separate substation-asset and vegetation past-due-work-order sections track?"
- Count-preserving reference: "The WMP reports that a tree fell onto an overhead distribution line; fuses on two conductors operated, the third did not, and the energized line ultimately ignited the fire. Separately, page 354 tabulates past-due substation asset work orders by age and priority, while page 446 describes vegetation work orders and past-due reporting by age, HFTD tier, and priority. The WMP does not say these backlog processes would have prevented the Dixie Fire's fuse behavior."

## Correct and retain

### `wmp_q35`

- Correct expected pages: `[392]`; remove pages 325 and 505.
- Evidence: `PGE-00411` states that recurring remote sensing may change the annual cadence and then gives the required update topics.
- Reference: current reference is materially accurate and can be retained.

### `wmp_q37`

- Correct question: "What qualifications and wildfire-specific certification requirements does the WMP list for Troublemen, and which causes are included in the HFTD/HFRA distribution ignition-rate calculation?"
- Correct expected pages: `[309, 379]`; remove page 559, which contains disaster billing material (`PGE-00591`, `PGE-00592`).
- Evidence: `PGE-00323`/`PGE-00324` define distribution ignition-rate inclusion rules; `PGE-00396` gives workforce qualifications.
- Corrected reference: "Troublemen are QEWs, and the WMP says their work is important to safe equipment operation and wildfire-risk mitigation, although they have no wildfire- or PSPS-specific certification beyond QEW. Separately, PG&E calculates the HFTD/HFRA distribution ignition rate from CPUC-reportable ignitions caused by equipment failure or overload and utility operation, divided by HFTD/HFRA failures per year. These passages establish that qualified operation and maintenance address the types of equipment events counted by the metric; the WMP does not quantify a causal effect of Troublemen qualifications on the rate."

### `wmp_q40`

- Correct question: "How does PG&E's quarterly compliance reporting differ between defined WMP targets and additional wildfire-related activities described in the plan?"
- Correct expected pages: `[505]`; remove pages 13 and 340.
- Evidence: `PGE-00528` says all targets are reported through QDR, QN, and ARC, while additional activities that are not defined targets are not reported through those mechanisms.
- Corrected reference: "PG&E will use all defined targets for quarterly compliance reporting through QDR, QN, and ARC. It will not report additional wildfire-related activities through those mechanisms when they are descriptions of plans rather than defined targets, and their timing and scope may change. The page does not say those activities are exempt from all other monitoring or work-order controls."

### `wmp_q41`

- Correct expected pages: `[54, 101]`; remove page 505.
- Evidence: `PGE-00056` gives the WFC inputs; `PGE-00099` states that WFC produces geospatial consequence results and that modeled pixel and asset risk are then aggregated to circuit segments.
- Corrected reference: "The WFC Model produces consequence values for ignition locations from simulated fire outcomes using detailed fuels, weather, and topography data. Within WDRM, WFC/CoRE results are combined with likelihood and ignition-probability results at asset and 100 m by 100 m pixel locations. PG&E then sums intersecting pixel risk and assigned asset risk along a circuit segment to obtain aggregated circuit-segment risk. Thus WFC consequence results are inputs to risk that is later aggregated; aggregated circuit risk does not feed into WFC."

### `wmp_q43`

- Correct question: "What reliability did PG&E report for Remote Grid customers in 2023 and 2024, and what continuation and system-integration updates does it describe?"
- Correct expected pages: `[238]`; remove pages 1 and 13.
- Evidence: `PGE-00246` reports 99.7%/99.83% reliability, elimination of exposure to upstream weather/tree-strike outages for remote-grid customers, continuation of the program, and operational-system integration.
- Corrected reference: "PG&E reports overall Remote Grid customer reliability of 99.7% in 2023 and 99.83% in 2024. These customers are no longer subject to outages caused by weather, tree strikes, or impacts to the former overhead distribution circuit. PG&E plans to continue the program in its current form and has integrated Remote Grid monitoring with SAP, EDGIS, the Outage Management Tool, and the Hazard Awareness and Warning Center to improve response, restoration, and asset management."

### `wmp_q44`

- Correct expected pages: `[325, 408]`; remove page 392.
- Evidence: `PGE-00428` states the PRC 4292 clearance rules and covered equipment; `PGE-00338` explicitly says transmission-switch failure-rate outages exclude vegetation and third-party damage.
- Corrected reference: "PRC 4292 pole clearing removes flammable vegetation around applicable poles or towers supporting equipment such as switches, fuses, transformers, arresters, junctions, and dead ends. This is a complementary risk-control activity, but it is not counted as a vegetation component of the transmission-switch failure-rate metric. PG&E's switch failure-rate calculation includes outages attributed to equipment failure, non-lightning weather, contamination, and unknown/other causes and explicitly excludes vegetation and third-party damage. Switch remediation is driven by inspection findings under the cited maintenance procedures."

### `wmp_q45`

- Correct question: "How does PG&E use LiDAR-based pole-loading results to prioritize risk, and what does the WMP separately report for System Hardening Target GH-12?"
- Correct expected pages: `[226, 281]`; remove page 446.
- Evidence: `PGE-00292` describes the LiDAR/pole-loading prioritization; `PGE-00232` reports GH-12 mileage and expected reliability benefit.
- Corrected reference: "PG&E uses LiDAR measurements as inputs to pole-loading calculations. Overloaded poles have a higher probability of failure, and PG&E compares their locations with wildfire ignition-consequence profiles to aid prioritization. Separately, PG&E reports approximately 1,230 miles of hardened overhead conductor installed since 2018 under GH-12, including about 145 miles in 2023 and 108 miles in 2024, and expects this activity to improve reliability. The cited text does not state that the LiDAR analysis selected those particular GH-12 miles."

### `wmp_q46`

- Correct question: "How does the covered-conductor program relate to GH-12, and what does the WMP say about current and completed effectiveness evaluations?"
- Correct expected pages: `[226, 588]`; remove page 420.
- Evidence: `PGE-00232` gives mileage and the ongoing reliability-quantification effort; `PGE-00621` lists GH-02 and GH-03 in a table of completed WMP activities.
- Corrected reference: "PG&E reports approximately 1,230 miles of hardened overhead conductor installed since 2018 under GH-12, including about 145 miles in 2023 and 108 miles in 2024. It expects improved reliability and says it is working to quantify reliability improvements on covered-conductor and undergrounded segments. GH-02 (Evaluate Covered Conductor Effectiveness) and GH-03 (Evaluate and Implement Covered Conductor Effectiveness Impact on Inspections and Maintenance Standards) are listed as completed activities, with completion years 2025 and 2023 respectively; they are not future planned activities."

### `wmp_q47`

- Correct question: "How are Resource Conservation District and Tribal-government vegetation partnerships similar in compliance reporting, and how do their operational emphases differ?"
- Correct expected pages: `[420, 421, 431, 505]`; add page 421.
- Evidence: `PGE-00443` marks Tribal work non-compliance-driven and describes capacity/roadside treatment; `PGE-00444` does the same for RCD fuels treatment; `PGE-00457` gives project details; `PGE-00528` gives the reporting rule for non-target activities.
- Corrected reference: "Both partnership types are described as non-compliance-driven fuels-treatment work. Page 505 says additional activities that are not defined targets are not reported through QDR, QN, or ARC, so the cited passages do not establish different quarterly reporting treatment. Operationally, Tribal collaborations emphasize building fire/fuel-crew capacity and roadside projects that improve ingress and egress, while RCD grants fund specific fuels-treatment and roadside-brushing projects, including the anticipated 70-acre Spanish Flats/Traverse Creek treatment and two Nevada County roadside miles."

### `wmp_q49`

- Correct question: "What does PG&E report about hardened-overhead-conductor mileage and reliability, and what does its illustrative risk-reduction calculation show?"
- Correct expected pages: `[187, 188, 226]`; remove page 264 and add the disclaimer page 187.
- Evidence: `PGE-00232` gives mileage/reliability; `PGE-00188` says the example values are illustrative and not necessarily commitments or targets; `PGE-00189` gives 25 x 98% = 24.5.
- Corrected reference: "PG&E reports approximately 1,230 miles of hardened overhead conductor installed since 2018 under GH-12, including about 145 miles in 2023 and 108 miles in 2024, and says the activity is expected to improve reliability. Separately, Table PG&E-6.2.1.2-2 illustrates calculation mechanics: applying an illustrative 98% effectiveness to 25 units of targeted WDRM risk exposure yields 24.5 units of workplan wildfire-risk reduction. The preceding text says these example values do not reflect specific commitments and do not necessarily align with WMP targets; they are not a measured 98% outcome for the installed GH-12 miles."

### `wmp_q50`

- Correct question: "What is PG&E's total projected WMP expenditure for 2026-2028, in millions of dollars?"
- Correct expected pages: `[53]`; PDF page 53 contains Table 3-3, while page 52 contains the preceding performance metric.
- Evidence: `PGE-00055`/PDF page 53 gives $5,513.330 million, $6,449.108 million, and $6,912.424 million.
- Reference: "PG&E's currently projected WMP expenditures total $18,874.862 million for 2026-2028: $5,513.330 million in 2026, $6,449.108 million in 2027, and $6,912.424 million in 2028. The WMP notes that later regulatory decisions may revise these projections."

### `wmp_q51`

- Correct question: "Does the WMP identify the programming language used for FPI 5.0, and which model and geospatial frameworks does it name?"
- Expected pages: retain `[496]`.
- Evidence: `PGE-00519` names a balanced random-forest framework and Uber's open-source H3 grid framework but no programming language.
- Reference: "The WMP does not identify a programming language. It says FPI 5.0 uses a multiclass balanced random-forest model based on decision trees and aggregates fuel/topography features to 0.7 km2 hexagons using Uber's open-source H3 framework."

### `wmp_q56`

- Correct question: "What survey-based evaluation of PSPS communications does PG&E report, and does the WMP provide numerical survey results?"
- Expected pages: retain `[532, 541, 550]`.
- Evidence: `PGE-00561` describes annual education/outreach surveys; `PGE-00571` describes pre/post-season KPI and post-event customer/CBO surveys; `PGE-00582` lists additional survey channels and external AFN reporting.
- Corrected reference: "PG&E reports annual PSPS education/outreach surveys, pre- and post-season surveys used as a KPI for AFN preparedness and resource awareness, post-event surveys of impacted customers and CBOs, and CRC-attendee surveys. It says feedback is used to identify improvements and points to AFN quarterly progress reports, but the WMP pages do not provide detailed numerical survey results. These passages document survey-based evaluation, not a separately identified formal human-factors study."

### `NEG-004` (answerable negative, not an unanswerable control)

- Correct expected pages: `[34, 41]`.
- Evidence: `PGE-00037` says PG&E will "strive to get to zero" while retaining containment/response capacity and describes a framework to minimize ignition risk; `PGE-00043` states the statutory and plan goal is to minimize catastrophic-wildfire risk, not guarantee zero ignitions.
- Corrected reference: "No. The WMP says PG&E will strive to get to zero ignitions, but it also plans containment and rapid-response measures because an ignition may still occur. Its stated statutory and plan goal is to minimize catastrophic-wildfire risk and reduce ignitions, not to guarantee zero equipment-caused ignitions."

### `wmp_q39`

- Correct question: "What does the WMP report about (a) combined covered-conductor/EPSS/DCD effectiveness, (b) Tribal vegetation-management partnerships, and (c) weather-station monitoring and escalation?"
- Expected pages: retain `[159, 420, 491]`.
- Evidence: page 159 (`PGE-00158`) gives the 79% estimate; page 420 (`PGE-00443`) describes Tribal crew and roadside-treatment partnerships; page 491 (`PGE-00513`) describes 10-minute station-data checks and ENOC escalation.
- Corrected reference: "PG&E estimates covered conductor combined with EPSS and DCD is approximately 79% effective at reducing ignition risk. Tribal partnerships support fire/fuel-crew capacity and roadside treatments that improve ingress and egress while reducing risk to and from PG&E assets. Separately, an external vendor collects weather-station data every 10 minutes, runs automated health checks, and escalates verified anomalies to PG&E's Enterprise Network Operations Center for a local technician to resolve."

## Unanswerable controls: retain

All controls should continue to use `expected_pages: []`. Nearby passages were reviewed to ensure that cadence, framework, collaboration, or generic environmental text was not mistaken for the requested absent fact.

| QID | Decision | Source check |
|---|---|---|
| `NEG-001` | Retain unanswerable | Page 159 (`PGE-00158`) labels $3.0M/mile as **PG&E's** estimate. Page 580 (`PGE-00613`) discusses undergrounding best-practice meetings with SCE but gives no SCE unit cost. |
| `NEG-002` | Retain unanswerable | Table 3-3 on page 53 (`PGE-00055`) contains projected 2026-2028 expenditure only; the WMP cannot contain actual FY2030 expenditure. |
| `NEG-003` | Retain unanswerable | The CERP has generic cyber-attack/all-hazards language and pages 557-559 discuss billing support, but no passage describes cybersecurity controls for the customer billing system. |
| `NEG-005` | Retain unanswerable | Butte County and tree-work passages exist, but no daily county schedule or March 15, 2026 tree count exists. |
| `wmp_q52` | Retain unanswerable | Page 488 (`PGE-00510`) gives 24 simulations/day, grid size, forecast-output volume, storage, and cost limitations, not wall-clock hours for one weather-model iteration. |
| `wmp_q53` | Retain unanswerable | Carbon/GHG passages concern microgrids, fuels treatment, and wildfire emissions (`PGE-00254`, `PGE-00447`), not a 2026-2028 undergrounding-project carbon footprint. |
| `wmp_q54` | Retain unanswerable | Pages 594-596 (`PGE-00627`) describe qualitative cross-utility collaboration; page 493 (`PGE-00516`) notes FPI benchmarking with SDG&E. No quantitative comparison of utilities' risk methodologies is provided. |
| `wmp_q55` | Retain unanswerable | Page 496 (`PGE-00519`) calls H3 and the balanced random forest open source, and page 140 (`PGE-00136`) mentions a Foundry-based UI, but no software-license terms are named. |
| `wmp_q57` | Retain unanswerable | Page 488 (`PGE-00510`) discusses computational/storage cost and data volume, not annual MWh consumption for model infrastructure. |
| `wmp_q58` | Retain unanswerable | Page 490 (`PGE-00512`) says a vendor runs WRF for partners worldwide, and pages 594-596 discuss other US utilities; neither explains international adaptation of PG&E's mitigation strategy. |
| `wmp_q61` | Retain unanswerable | General carbon passages do not quantify annual avoided CO2 from undergrounding versus overhead lines. |
| `wmp_q63` | Retain unanswerable | Page 502 (`PGE-00526`) gives twice-daily FPI forecasts and a forecast horizon, not wall-clock runtime on a standard server. |
| `wmp_q64` | Retain unanswerable | Page 493 (`PGE-00516`) mentions NWCG courses and the National Fire Danger Rating System but no governing license or licensing agreement. |
| `wmp_q65` | Retain unanswerable | The WMP contains no Australia- or Mediterranean-utility methodology comparison; worldwide WRF-vendor experience is not such a comparison. |

## Required rerun consequences

Any question, reference-answer, answerability, or expected-page change produces a new benchmark version and hash. Retrieval summaries computed against `wmp_okf_pge_97_v1` must not be reported as results for the corrected benchmark. Because several question texts also change and four items are removed, generation and judging should be rerun from a clean output directory after the revised benchmark passes a second semantic review. The existing partial generation is diagnostic only.

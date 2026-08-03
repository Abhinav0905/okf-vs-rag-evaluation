---
type: Document Section
title: 5.2.3 Key Assumptions and Limitations
resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#section=5-2-3-key-assumptions-and-limitations
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
  resource: urn:sha256:e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a#pages=106,107,108,109,110,111,112,113
  title: pge-2026-2028-base-wmp-vol1-r0.pdf
corpus: PGE
corpus_version: pge_wmp_r0_20260719
source_chunk_id: PGE-TOPIC-00065
slug: 5-2-3-key-assumptions-and-limitations
outline_level: 3
outline_order: 65
section_number: 5.2.3
section_path:
- 5. Risk Methodology and Assessment
- 5.2 Risk Analysis Framework
- 5.2.3 Key Assumptions and Limitations
page_number: 106
page_numbers:
- 106
- 107
- 108
- 109
- 110
- 111
- 112
- 113
document_name: pge-2026-2028-base-wmp-vol1-r0.pdf
source_sha256: e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a
content_sha256: c0976ec25effc46df74fc25df9eba8cfca7db6c4da8e15872530cda8b760d425
child_count: 0
---

# 5.2.3 Key Assumptions and Limitations

## Evidence

<!-- okf-trial:evidence-start -->
Since the individual elements of risk assessment are interdependent, the interfaces 
between the various risk models and activities must be internally-consistent.  In this 
section of the WMP, the electrical corporation must discuss key assumptions, 
limitations, and data standards for the individual elements of its risk assessment.27  
This must include the following:

• 
Key modeling assumptions made specific to each model to represent the physical 
world and to simplify calculations;

• 
Data standards, which must be consistently defined (e.g., weather model 
predictions at a 30-foot (ft.) [10-meter] height must be converted to the correct 
height for fire behavior predictions, such as mid-flame wind speeds);

• 
Consistency of assumptions and limitations in each interconnected model, which 
must be traced from start to finish, with any discrepancies between models 
discussed;

• 
Stability of assumptions in the program, including historical and projected changes; 
and

• 
Monetization of attributes, if utilized, including (if applicable) the selected value of 
statistical life, dollar value of injury prevention, and dollar value of reliability risk.

More developed activities (programs) regularly monitor and evaluate the scope and 
validity of modeling assumptions.  Monitoring and evaluation categories may include:

• 
Adaptation of weather history to current and forecasted climate conditions;

27 Pub. Util. Code § 8386(c)(4).

-76-

• 
Availability of suppression resources including type, number of resources, and ease 
of access to incident location;

• 
Height of wind driving fire spread including any wind adjustment factor calculations;

• 
General equipment failure rates based on historical trends for equipment type, 
equipment age, overdue maintenance, and any wind speed functional 
dependences;

• 
General vegetation contact rates based on historical trends for vegetation species, 
vegetation height, and environmental factors such as wind speed functional 
dependences;

• 
Height of electrical equipment in the service territory;

• 
Stability of the atmosphere and resulting calculation of near-surface winds;

• 
Vegetative fuels including models that account for fuel management activities by 
other land managers (e.g., thinning, prescribed burns);

• 
Combination of risk components and weighting of attributes and resulting impacts;

• 
Wind load capacity for electrical equipment in the service territory;

• 
Number, extent, and type of community assets at risk in the service territory;

• 
Proxies for estimating impact on customers and communities in the service territory; 
and

• 
Extent, distribution, and characteristics of vulnerable populations in the service 
territory.

The electrical corporation must document each assumption in Table 5-1.  The electrical 
corporation must summarize assumptions made within models in accordance with the 
model documentation requirements in Appendix B.

-77-

Table 5-1 below shows our risk modeling assumptions and limitations.

TABLE 5-1:  
RISK MODELING ASSUMPTIONS AND LIMITATIONS 13

Assumption 
Rationale/Justification 
Limitation 
Applicable Model

It is assumed that events from June-November, 
the typical timing of fire seasons, are 
representative of all events capable of 
producing wildfire risk

If the training data for the WDRM included 
events caused by winter storms, icing, and 
other causal processes not compatible with 
ignition and wildfire spread, the pattern of 
model predictions would be influenced by 
events that contribute little or no wildfire risk.  
To avoid exposing the model to misleading 
data, the training events are restricted to 
June through November.

We assume that wildfires are 
possible outside of the typical fire 
season and that ignitions and 
wildfires occurring outside of the 
typical fire season would have the 
same relationship with the model 
covariates as the ones the model 
is already trained on.

Overall Utility Risk

Ignition/Wildfire Risk 
(WDRM/WTRM)

Ignition Likelihood

Ignition/WFC

Equipment 
Likelihood of Ignition

Contact from Object 
Likelihood of Ignition

-78-

The WDRM v4 is an “observational model” that 
uses the pattern of past outages and ignitions to 
predict their future.

The core assumption of such an approach is 
that the correlations and causal processes 
that have governed past outages and 
ignitions will continue to govern them in the 
future.

N/A 
WDRM

Ignition Likelihood

Equipment 
Likelihood of Ignition

Contact from Object 
Likelihood of Ignition

TABLE 5-1:   
RISK MODELING ASSUMPTIONS AND LIMITATIONS

(CONTINUED)

Assumption 
Rationale/Justification 
Limitation 
Applicable Model

ML tools, like feature generation, model 
regularization, and the preferential use of out of 
sample performance metrics, are well suited to 
the prediction of ignition probability and risk.

The key features of the ML tools are the 
primary output of the WDRM v4.

N/A 
Ignition/Wildfire Risk 
(WDRM)

Ignition Likelihood

Equipment 
Likelihood of Ignition

Contact from Object 
Likelihood of Ignition

WTRM builds on assumptions used by the 
Transmission Operational Assessment (OA) 
Model.  PG&E identified 47 components 
through a Failure Modes and Effects Analysis 
which could result in a wildfire ignition if they 
failed.  These 47 components were divided into 
9 asset groups and asset specific datasets are 
assigned to each one.

While the scope of the WTRM exceeds that 
of the OA Model in terms of incorporating 
other hazards, the asset group types remain 
a proxy for a collection of components that 
share similar:  (1) life cycles, (2) sensitivities 
to threats and hazards, and (3) Asset 
Management strategies.

N/A 
Ignition/Wildfire Risk 
(WTRM v2)

-79-

Where age data is unavailable from system of 
records, a logic is used to determine the most 
conservative age of the asset.

Age data is required for each component for 
the WTRM to compute an annual failure rate.

Some equipment risk could 
potentially be overestimated due to 
equipment using assumed age.

Ignition/Wildfire Risk 
(WTRM v2)

The inclusion of “PICs Analysis” does not 
change the overall PSPS MAVF Risk Score.

While a large set of customers are being 
included as having PSPS impact, when 
calibrating the PSPS Risk Score in terms of 
MAVF, the overall risk is represented by 
historical performance.  As such, all 
customers see a smaller contribution to the 
overall risk score, in which the overall risk 
scores do not change.

Additional scenarios being 
considered have no impact to the 
overall PSPS MAVF risk score.

PSPS Risk

PSPS Consequence

PSPS Likelihood

Vulnerability of 
Community to PSPS

TABLE 5-1:   
RISK MODELING ASSUMPTIONS AND LIMITATIONS

(CONTINUED)

Assumption 
Rationale/Justification 
Limitation 
Applicable Model

Circuits operating outside their rated capacity or 
in abnormal configuration do not have an 
increased ignition risk.

In July 2024 during an intense heat event, 
PG&E saw a significant uptick in fire risk 
exposure and associated ignition events.  
PG&E did an analysis that found that 
conductors and connectors under high heat 
stress, both external (due to extended heat) 
and internal (due to load) could be one of the 
contributing factors.

While the distribution (WDRM v4) 
probability of failure model does 
include the risk for abnormal 
circuits, it does not currently 
identify circuits that are operating 
within the rated capacity and 
circuits that are operating outside 
their rated capacity or circuits in 
abnormal configuration.  PG&E is 
currently investigating if there is a 
correlation between circuit 
condition and higher outage and 
ignition events.  PG&E is collecting 
data to determine the degree of 
risk introduced by circuit 
configuration in the HFTD/HFRA.

WDRM v4

-80-

“Potentially-impacted customers” (PIC) is 
created as a 1 in 13-year frequency.  Outage 
Duration is based on average outage duration 
from “12 year PSPS lookback”.

“Potentially-impacted customers” inherently 
do not show up in the “12-year PSPS 
lookback.”  As such, the frequency of an 
event is 1-year exceeding PG&E’s lookback 
period to capture the potential for additional 
customers to be impacted.  This is to capture 
the non-zero PSPS risk tied to customers 
that do not show up on the lookback.

The accuracy of the PICs is based 
on the 12-year lookback data.

PSPS Risk

PSPS Consequence

PSPS Likelihood

Vulnerability of 
Community to PSPS

TABLE 5-1:   
RISK MODELING ASSUMPTIONS AND LIMITATIONS

(CONTINUED)

Assumption 
Rationale/Justification 
Limitation 
Applicable Model

Critical Customer Weightings are based on 
high level SME judgement.

The assignment of a critical weighting factor 
to our customers is a subjective process 
that will continually be reviewed and 
potentially updated.  There has been limited 
industry research and therefore no industry 
standard on how different customers are 
impacted by PSPS events or loss of power.  
PG&E will continue to work with the industry 
and Investor-Owned Utility (IOU) partners to 
better reflect customer risks in our PSPS 
consequence model.  The current weighting 
system was developed internally to provide 
a simple differentiation of customer category 
types.

The distribution of customer risk 
(and PSPS risk reduction) is 
partly driven by the type of 
customers and their critical 
weighting score.  Significant 
changes to the critical customer 
weighting could potentially impact 
Circuit Protection Zone risk 
ranking and prioritization 
initiatives

PSPS Risk

PSPS Consequence

PSPS Likelihood

Vulnerability of 
Community to PSPS

PSPS safety consequence is based off 
50 percent PG&E PSPS planned and 
50 percent unplanned long duration outages 
across the United States (U.S.)

PSPS represented as a non-zero safety risk 
is reasonable.  However, PG&E providing 
advanced notification for a planned 
de-energization reduces the safety impact of 
the outage and should not be treated as an 
unplanned outage.  Given that historical 
records show no safety impacts, PG&E 
included unplanned long duration outages 
across the U.S. (i.e., 2033 NE Blackout, 
2011 SW Blackout, 2012 Superstorm 
Sandy, etc.) at 50 percent, respectively.

The safety consequence of PSPS 
should not include unplanned 
outages as it does not accurately 
represent PSPS itself.

PSPS Risk

-81-

PSPS Consequence

PSPS Likelihood

Safety accounts for 50 percent of our MAVF 
PSPS Risk.  PSPS events are relatively new 
and there is minimal SIF data to include in the 
risk analysis.  For this reason, other large 
external national events (i.e., 2003 NE 
Blackout, 2011 SW Blackout, 2012 Superstorm 
Sandy, etc.) were considered in evaluating 
safety risks associated with PSPS events.

Vulnerability of 
Community to PSPS

EPSS Consequence assumes that the duration 
will be the same for outages that occur both 
with and without EPSS enabled.

Analysis of outages supports the 
expectation that the duration of an outage 
will be the same whether or not EPSS is 
enabled.

As future operational EPSS data 
becomes available, analysis may 
discover differences in duration 
for EPSS enabled outages

EPSS Risk

EPSS Consequence

EPSS Likelihood of a fault is independent of 
whether or not EPSS is enabled.

No known causal mechanism that would 
cause the fault rate to change when EPSS 
is enabled.

As future operational EPSS data 
become available a causal 
mechanism may be discovered.

EPSS Risk

EPSS Likelihood

TABLE 5-1:   
RISK MODELING ASSUMPTIONS AND LIMITATIONS

(CONTINUED)

Assumption 
Rationale/Justification 
Limitation 
Applicable Model

EPSS Value of Service (VOS) is specific to 
customer class based on the outputs of the 
interruption cost estimation calculator

Interruption cost estimation calculator inputs 
are based on PG&E customer 
characteristics and historic SAIFI, SAIDI, 
CAIDI metrics

VOS is based on 2016 data, 
escalated to 2024 values

EPSS Risk

EPSS Consequence

Baseline Risk in the Enterprise Wildfire Risk 
Model is calibrated to historical performance.

Baseline wildfire risk needs to be calibrated 
against all other risks within the Company.  
As such, historical years’ performance is 
used to calculate risk score

Changes in wildfire risk has been 
dynamic.  Baseline risk scores 
based on historical performance 
may not be reflective of current 
performance.

Enterprise Risk 
Model (a)

The FPI and IPW models are observational 
models that learn the pattern of historical fires, 
outages, and ignitions together with the 
conditions under which they occurred to predict 
future fires, outages, and ignitions.

The rationale of such an approach is that the 
correlations and causal processes that drive 
historical fires, outages and ignitions will 
continue to drive them in the future.

Fires, ignitions and outages of the 
future may be driven by processes 
that have not been accounted for 
in the models.

FPI/IPW(b)

The FPI and IPW models are driven 
predominantly by weather model forecasts.

Weather is an important driver of fires, 
outages, and ignitions.

Weather model forecasts, while 
skillful and well validated, are not a 
perfect representation of the future 
state of the atmosphere.

FPI/IPW(b)

-82-

ML methods, such as feature creation, 
classification and regression, model sampling, 
and use of the out of sample performance 
metrics, are well suited to the prediction of fire, 
outage, and ignition probability and risk.

The rationale of ML is that it allows the skillful 
explanation of future fires, outages, and 
ignitions by using large amounts of data and 
sophisticated algorithms.

ML models are limited by the 
amount of data available and the 
sophistication of the current 
state-of-the-art algorithms.

FPI/IPW(b)

_______________

(a) The Enterprise Risk Model is used to calibrate all the wildfire, PSPS, and EPSS risk models listed in Table 5-4 above for the purpose of calculating

overall utility risk. 
(b) The FPI/IPW models are operational models and, therefore, do not appear in Table 5-4 below.

5.3 
Risk Scenarios
<!-- okf-trial:evidence-end -->

## Relationships

* Parent topic: [5.2 Risk Analysis Framework](../5-2-risk-analysis-framework.md)
* Previous topic: [5.2.2 Risk and Risk Components Calculation](5-2-2-risk-and-risk-components-calculation.md)

## Provenance

Extracted from **pge-2026-2028-base-wmp-vol1-r0.pdf**, pages 106-113.[^source-pdf]

[^source-pdf]: pge-2026-2028-base-wmp-vol1-r0.pdf, pages 106-113.

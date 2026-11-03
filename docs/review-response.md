# What the feedback tests, and what changed

The assessment tests whether a candidate preserves meaning, can recover after a failed load and can support a conclusion with evidence. A green run with incorrect denominators would fail that standard. Tool count adds no value by itself.

| Feedback | Decision and reason |
|---|---|
| Candidate database and atomic publication | Implemented together. A complete candidate database, CSV set and run manifest move into a published run directory. One LATEST pointer selects all of them. This avoids trying to atomically swap a database and fifteen separate CSV files independently. |
| Result-only PDF | Implemented. The renderer verifies output hashes and reads published SQL outputs for satisfaction, medians and web sensitivity. A different GSS_DB is rejected. |
| Input manifest | Implemented. docs/extracts.csv pins reviewed source bytes, counts, years, variables and export settings. A deliberately corrected source requires reviewing and updating its checksum, then rebuilding. |
| Generate wide projections from seeds | Implemented through wide_label, wide_value and wide_status flags. These are explicit projection roles, because some variables need both a readable label and a numeric code. |
| Ballot metadata | Implemented an eligibility seed keyed by variable, year, ballot and form. A single valid_ballots column would lose the 2014/2016 form changes. |
| Distinguish .i reasons | Implemented a derived not_asked_ballot status only when an explicit reviewed eligibility rule excludes the combination. source_status retains the raw codebook meaning. Unknown eligibility remains unknown. |
| Stronger Q4 wording | The observed rank association is very small (rho about -0.011). Kept the design caveat. A rough independent-sample interval cannot establish an equivalence claim for the population without design-based uncertainty and a prespecified meaningful-effect threshold. |
| Claim the adjusted Q6 z is probably lower | Rejected that prediction. Weights can change the estimated difference and survey design can change its error. Both require calculation. The report identifies the 2.67 figure as exploratory. |
| EVWORK universe and work-status code 3 | Confirmed from NORC's codebook. Code 3 explicitly retains a job during absence. Added a sensitivity query rather than assuming unchanged outputs. |
| Hash lockfile and CI | Added requirements.lock with release wheel hashes and used it in the clean-install workflow. Hosted CI must be observed before claiming it passed. |
| Docker | Omitted. The brief permits a pinned local environment. A verified clean workflow supplies direct reproducibility evidence without another installation path. |
| Batch-status architecture | Deferred. Full reconstruction of 10,620 raw memberships is affordable. Candidate publication avoids maintaining a rejected/validated state machine in this exercise. |

## Work-status sensitivity

There are 150 interviews coded with a job but temporarily absent. Removing them from employment reduces the Q4 complete-case sample by 89 (2,845 to 2,756) and changes group means. Q3's leading industry labels stay the same, with different counts. Q5's observed valid-answer percentage remains 90.50%, but its all-nonworker bounds change from 81.31–91.46% to 77.48–91.87%. These changes are reproduced in 14_work_status_sensitivity.csv.

Thus, the request to prove that reclassifying code 3 changes nothing is incorrect. The source definition remains the basis for including it; the sensitivity quantifies consequences.

## Source definitions and weights

NORC's codebook labels code 3 as having a job during temporary absence. It directs EVWORK to retired people, students, homemakers and the other nonworking category. Codes 1–4 are inapplicable to that question. The source is the codebook's WRKSTAT/EVWORK section around printed pages 123–124. [NORC cross-section codebook main body](https://gss.norc.org/content/dam/gss/get-documentation/pdf/codebook/GSS_Codebook_mainbody.pdf).

The selected years are cross-sectional interviews. NORC's 2020 panel primer distinguishes the original 2016 and 2018 cross sections from their later reinterviews. [Panel primer](https://gss.norc.org/content/dam/gss/get-documentation/pdf/other/2020%20Panel%20Methodological%20Primer.pdf).

WTSSPS is the primary point-estimate convention here, following the FAQ. WTSSNRPS adds the geographic nonresponse adjustment and is the sensitivity estimate. NORC's codebook and earlier memo prefer NRPS where available. Both new weights incorporate the ballot/form corrections affecting 2016 and 2018. The choice is documented rather than treated as unanimous guidance. [FAQ](https://gss.norc.org/faq.html), [weight memo](https://gss.norc.org/content/dam/gss/get-documentation/pdf/reports/methodological-reports/MR135%20poststratified%20weights.pdf).

## Remaining boundaries

- Candidates rebuild all data. At full scale, wave partitions and incremental processing may become worthwhile after measurement.
- Atomic rename relies on a local same-filesystem operation. Readers resolve LATEST once. A lock prevents overlapping local builds; interrupted locks need operator review.
- Database and CSV hashes detect changes in published outputs. A manifest establishes provenance for the reviewed export, not independent truth about the source system.
- Ballot/form metadata is scoped to these reviewed waves. New wording, sources or waves require a fresh eligibility review.
- VSTRAT/VPSU are still absent from the committed extracts, so population-level standard errors remain future work.
- The benchmark measures incremental table build time, checkpoint and storage against a view. Its break-even estimate applies to repeated reads of the measured query; it excludes dbt startup, upstream table costs and monetary storage cost.

## Follow-up review fixes

- **A/B population:** Q7 filters memberships and its respondent grain check to the required A/B pair. A third-cut regression includes one shared and one new interview; a duplicate in the pair still fails the grain check. Global uniqueness remains a separate dbt test.
- **Report freshness:** the temporary-absence count is published by SQL 12, and the newspaper standard-error distance is read from SQL 06. A renderer regression changed both values in a disposable publication and verified the PDF followed them.
- **Materialization cost:** the benchmark uses three isolated databases per model, measuring CTAS plus checkpoint and file growth relative to a view. It publishes machine-readable evidence, checks equal query results, and records break-even reads for the table that changed in the selected comparison. Inputs, dbt models/seeds/macros and query hashes bind the evidence to the publication. No orchestration or infrastructure was added.

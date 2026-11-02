# Reading the survey results

Each row of respondents is one (survey year, respondent ID) interview. Q1-Q6 aggregate this table. Reported percentages are unweighted and denominators vary by question. See the [original pre-build profile](../../docs/profile.md) and [missing counts by variable and year](../../docs/profile.csv).

| File | Population and interpretation |
|---|---|
| 01_prayer | Both upbringing and prayer answered. Each percentage is within an upbringing group. An unlisted frequency had no observations in that group. |
| 02_afterlife | Yes divided by yes + no. Missing types are counted separately. No one was coded as not asked by year in these waves. |
| 03_industry | Currently working with both degree and industry. Shows the largest count for each degree, including every industry tied for first. No ties occurred here. |
| 04_tv_satisfaction / 04_tv_rank_tests | Currently working with valid TV hours and standard work satisfaction. The group means rise slightly, but neither test detects an association in these 2,845 interviews. Spearman uses higher ranks for greater satisfaction. Kruskal-Wallis compares ranked TV hours across all four groups, with ties corrected. Both p-values assume independent observations and omit survey weights, clustering and stratification. |
| 05_ever_work | Among 3,034 nonworkers, 306 looking for work were routed out and two eligible respondents lacked usable answers. The yes percentage is among 2,726 observed answers. Bounds use all 3,034, varying the 308 unknowns from all no to all yes. |
| 06_wave_changes | Complete cases separately for daily newspaper reading and TV hours. Deltas compare successive cross sections. The SE of a difference uses the sum of the independent wave mean variances (binomial for daily news, sample variance for TV). The 2014-16 news drop is 2.67 approximate SEs. All other changes are less than one. These are exploratory comparisons without survey-design or multiplicity adjustment. |
| 07_overlap | A/B membership counts and fractions plus the grain of the table underlying Q1-Q6. Using ID alone would collapse distinct interviews across waves. |
| 08_technology_interest | Section 1 supplement. Interest in new inventions and technologies among valid answers by wave and pooled. Coverage uses all interviews as denominator. |
| 09_ballot_coverage | Counts valid answers out of all interviews for each year, ballot and field. Ballot C has no valid NEWS, TVHOURS, COMPUSE or WWWHR in any selected year. INTTECH has a different ballot/form pattern. |

# Reading the survey results

**Where are the answers?** Open the [report](../survey-assessment.pdf). Section 6 summarizes the six analytical questions. Open the full results: [01 prayer by upbringing](01_prayer.csv), [02 afterlife by year, including not asked](02_afterlife.csv), [03 top industry by degree](03_industry.csv), [04 TV hours and satisfaction](04_tv_satisfaction.csv) and [rank tests](04_tv_rank_tests.csv), [05 work history among nonworkers](05_ever_work.csv), [06 changes between waves](06_wave_changes.csv). The queries have matching names in [dbt/analyses](../../dbt/analyses).

**The eleven questions about each respondent** are columns of the `marts.respondents` table in the published run database resolved through `build/LATEST`; section 2 of the report explains the field choices. To see actual answers instead of aggregates, run this read-only query after building the database:

```sql
select survey_year, respondent_id,
       wrkstat as working_status, evwork as worked_at_least_one_year,
       degree as highest_degree, educ_value as years_of_school,
       indus10 as reported_industry, satjob as work_satisfaction,
       postlife as afterlife_belief, pray as prayer_frequency,
       relig16 as religion_raised_in, news as newspaper_frequency,
       tvhours_value as tv_hours_per_day, inttech as technology_interest
from marts.respondents
order by survey_year, respondent_id
limit 10;
```

For a current industry, filter to `is_working`: nonworkers can report an earlier industry. EVWORK is not asked of current workers or job seekers, so their lifetime work duration cannot be inferred. The item asks about **at least one year**, not strictly more than 12 months. TVHOURS measures hours per day rather than viewing frequency. A null is not a “no”; the `marts.answers` table stores the reason under `status`, keyed by survey year, respondent ID and variable.

Each row of respondents is one (survey year, respondent ID) interview. Q1-Q6 aggregate this table. Columns starting `wtssps_` use the primary survey weight, and these are the figures the report quotes. Other percentages are unweighted, and raw counts stay alongside. Denominators vary by question. See the [original pre-build profile](../../docs/profile.md) and [missing counts by variable and year](../../docs/profile.csv).

| File | Population and interpretation |
|---|---|
| 01_prayer | Both upbringing and prayer answered. Each percentage is within an upbringing group. An unlisted frequency had no observations in that group. `is_small_group` flags groups under 50 people. |
| 02_afterlife | Yes divided by yes + no. Missing types are counted separately. No one was coded as not asked by year or ballot in these waves. |
| 03_industry | Currently working with both degree and industry. Ranks by weighted share and shows the runner-up, including every industry tied for first. No ties occurred here. `wtssps_lead_z` is the lead over the runner-up in approximate standard errors, using Kish effective n. |
| 04_tv_satisfaction / 04_tv_rank_tests | Currently working with valid TV hours and standard work satisfaction. Differences are small and the direction changes with weighting: unweighted means rise as satisfaction falls, weighted means fall. Neither rank test detects an association in these 2,845 interviews. Spearman uses higher ranks for greater satisfaction. Kruskal-Wallis compares ranked TV hours across all four groups, with ties corrected. Both p-values assume independent observations and omit survey weights, clustering and stratification. |
| 05_ever_work | Among 3,034 nonworkers, 306 looking for work were routed out and two eligible respondents lacked usable answers. The yes percentage is among 2,726 observed answers. Bounds use all 3,034, varying the 308 unknowns from all no to all yes. `wtssps_lower_bound_with_industry_pct` also counts job seekers with a recorded industry as having worked, which assumes that industry means at least a year of work. |
| 06_wave_changes | Complete cases separately for newspaper reading and TV hours. Changes compare successive cross sections. The SE of a difference sums the independent wave variances; weighted SEs use Kish effective n and omit strata and clusters. Under WTSSPS, never-reading rises by about 7 points per wave at 3 to 4 approximate SEs, daily reading falls about 2.8 points per wave at under 2 SEs and 5.6 points since 2014 at over 3 SEs (`wtssps_news_since_first_`), and TV changes by under one SE. Comparisons are exploratory, without multiplicity adjustment. |
| 07_overlap | Membership, fractions and respondent grain are restricted to the two cuts named in the `extract_cuts` seed. A third extract cannot change these populations. Global respondent uniqueness is checked separately by dbt. Using ID alone would collapse distinct interviews across waves. |
| 09_ballot_coverage | Counts valid answers out of all interviews for each year, ballot and field. Ballot C has no valid NEWS, TVHOURS, COMPUSE or WWWHR in any selected year. INTTECH has a different ballot/form pattern. |
| 10_weight_sensitivity | Headline Q2, Q3, Q5 and Q6 estimates under WTSSPS and WTSSNRPS, the difference, and whether each Q3 leader stays the same. |
| 12_report_summary | Published worker/satisfaction counts and median checks used by the PDF. |
| 14_work_status_sensitivity | Reclassifies temporarily absent workers to quantify changes to Q3-Q5, weighted and unweighted. |

To reproduce the TV medians in section 6, run this against the built database. A missing TV response does not exclude someone from `answered_satisfaction`.

```sql
select satjob, count(*) as answered_satisfaction, count(tvhours_value) as also_answered_tv,
       median(tvhours_value) as median_daily_tv_hours
from marts.respondents where is_working and satjob is not null
group by satjob order by satjob;
```

The current database and CSVs are selected together by source/snapshot.py. The PDF reads published CSV statistics exclusively. Its evidence on failures, scale and materialization comes from the files beside the report.

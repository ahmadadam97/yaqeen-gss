# Reading the survey results

**Where are the answers?** Open the [five-page report](../survey-assessment.pdf). Page 3 (**Findings**, sections 01-06) summarizes the six analytical questions. Open the full results: [01 prayer by upbringing](01_prayer.csv), [02 afterlife by year, including not asked](02_afterlife.csv), [03 top industry by degree](03_industry.csv), [04 TV hours and satisfaction](04_tv_satisfaction.csv) and [rank tests](04_tv_rank_tests.csv), [05 work history among nonworkers](05_ever_work.csv), [06 changes between waves](06_wave_changes.csv). The queries have matching names in [source/sql](../../source/sql).

**The eleven questions about each respondent** are columns of the `respondents` table in `build/gss.duckdb`; page 2 (**Coverage**) explains the field choices. To see actual answers instead of aggregates, run this read-only query after building the database:

```sql
select survey_year, respondent_id,
       wrkstat as working_status, evwork as worked_at_least_one_year,
       degree as highest_degree, educ_value as years_of_school,
       indus10 as reported_industry, satjob as work_satisfaction,
       postlife as afterlife_belief, pray as prayer_frequency,
       relig16 as religion_raised_in, news as newspaper_frequency,
       tvhours_value as tv_hours_per_day, inttech as technology_interest
from respondents
order by survey_year, respondent_id
limit 10;
```

For a current industry, filter to `is_working`: nonworkers can report an earlier industry. EVWORK is not asked of current workers or job seekers, so their lifetime work duration cannot be inferred. The item asks about **at least one year**, not strictly more than 12 months. TVHOURS measures hours per day rather than viewing frequency. A null is not a “no”; the `answers` table stores the reason under `status`, keyed by survey year, respondent ID and variable. [Technology interest by wave](08_technology_interest.csv) is a separate supplement.

Each row of respondents is one (survey year, respondent ID) interview. Q1-Q6 aggregate this table. Percentages are unweighted unless the column names a weight. Denominators vary by question. See the [original pre-build profile](../../docs/profile.md) and [missing counts by variable and year](../../docs/profile.csv).

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
| 10_prayer_afterlife | Belief by prayer group and wave. Counts distinguish valid prayer from valid belief. WTSSPS is primary; WTSSNRPS is a sensitivity check. This cannot establish cause or describe Muslims specifically. |
| 11_media_by_age | Daily newspaper share and median weekly non-email web time among the same people with known age and both answers. Counts show what is lost using paired responses. Web use does not measure access or preference. |

To reproduce the satisfaction rates and medians on page 3, run this against the built database. For the overall rate, sum the two satisfied categories and divide by all four categories in `answered_satisfaction`. For the TV comparison, repeat using `also_answered_tv`. A missing TV response does not exclude someone from the first rate.

```sql
select satjob, count(*) as answered_satisfaction, count(tvhours_value) as also_answered_tv,
       median(tvhours_value) as median_daily_tv_hours
from respondents where is_working and satjob is not null
group by satjob order by satjob;
```

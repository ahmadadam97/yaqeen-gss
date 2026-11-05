-- Q4: TV hours by work satisfaction among current workers. Effective n shows how much the weights reduce precision.
select
    'Currently working; valid TV and work satisfaction' as cohort,
    satjob as satisfaction,
    count(*) as group_n,
    round(avg(tvhours_value), 2) as mean_tv_hours,
    round(sum(wtssps_value * tvhours_value) / sum(wtssps_value), 2) as wtssps_mean_tv_hours,
    round(sum(wtssps_value) ^ 2 / sum(wtssps_value ^ 2), 0) as effective_n
from {{ ref('respondents') }}
where is_working
  and satjob is not null
  and tvhours_value is not null
group by satjob, satjob_value
order by satjob_value

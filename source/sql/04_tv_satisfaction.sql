select 'Currently working; valid TV and work satisfaction' as cohort,
       satjob as satisfaction, count(*) as group_n, round(avg(tvhours_value),2) as mean_tv_hours
from respondents
where is_working and satjob is not null and tvhours_value is not null
group by satjob order by mean_tv_hours, satisfaction

select count(*) as nonworking_n,
       count(*) filter (where ever_work_eligible) as eligible_n,
       count(evwork) as valid_n, count(*) filter (where evwork='YES') as yes_n,
       round(100.0*count(*) filter (where evwork='YES') / nullif(count(evwork),0),2) as yes_pct_of_valid,
       count(*)-count(evwork) as unknown_n,
       count(*) filter (where wrkstat_value=4 and evwork is null) as job_seekers_routed_out_n,
       count(*) filter (where ever_work_eligible and evwork is null) as eligible_missing_n,
       round(100.0*count(*) filter (where evwork='YES')/nullif(count(*),0),2) as lower_bound_pct,
       round(100.0*(count(*)-count(*) filter (where evwork='NO'))/nullif(count(*),0),2) as upper_bound_pct
from respondents where is_working=false

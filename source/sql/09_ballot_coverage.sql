select a.survey_year, r.ballot, a.variable, count(*) as interviews,
       count(*) filter (where a.status='answer') as valid_n,
       round(100.0*valid_n/count(*),2) as valid_pct
from answers a join respondents r using (survey_year, respondent_id)
where a.variable in ('news','tvhours','compuse','wwwhr','inttech')
group by all order by a.survey_year,r.ballot,a.variable

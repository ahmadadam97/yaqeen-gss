select survey_year, respondent_id from {{ ref('respondents') }}
where (evwork is not null and ever_work_eligible is distinct from true)
   or ((wwwhr_value is null or wwwmin_value is null) and web_hours_weekly is not null)
union all
select survey_year, respondent_id from {{ ref('answers') }}
where status='answer' and is_eligible is false

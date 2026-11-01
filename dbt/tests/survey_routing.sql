select survey_year, respondent_id from {{ ref('respondents') }}
where (evwork is not null and ever_work_eligible is distinct from true)
   or (ballot = 'Ballot c' and (news is not null or tvhours_value is not null or web_hours_weekly is not null))
   or ((wwwhr_value is null or wwwmin_value is null) and web_hours_weekly is not null)
   or (survey_year=2016 and ballot='Ballot a' and form='Alternate <y>' and satjob is not null)

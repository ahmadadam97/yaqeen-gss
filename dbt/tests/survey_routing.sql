-- Answers must follow the questionnaire's routing.
select survey_year, respondent_id
from {{ ref('respondents') }}
where (evwork is not null and ever_work_eligible is distinct from true)
   or (satjob is not null and satjob_eligible is false)
   or web_hours_weekly > 168

union all

-- No answer on a ballot/form excluded by a reviewed rule, and no ballot/form the rules do not cover.
select survey_year, respondent_id
from {{ ref('answers') }}
where (status = 'answer' and is_eligible is false)
   or (is_eligible is null and variable in (select variable from {{ ref('eligibility') }}))

union all

-- Someone who said they do not use the web cannot report web time.
select web_use.survey_year, web_use.respondent_id
from {{ ref('answers') }} as web_use
join {{ ref('answers') }} as duration using (survey_year, respondent_id)
where web_use.variable = 'usewww'
  and web_use.answer_label = 'NO'
  and duration.variable in ('wwwhr', 'wwwmin')
  and duration.answer_value > 0

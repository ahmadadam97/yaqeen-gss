with expected(raw_prefix, wanted) as (
    values ('.d:', 'dont_know'), ('.n:', 'no_answer'), ('.i:', 'inapplicable'),
           ('.y:', 'not_asked_year')
)
select answers.survey_year, answers.respondent_id, answers.variable
from {{ ref('answers') }} as answers
join expected on starts_with(answers.raw_label, expected.raw_prefix)
where answers.source_status <> expected.wanted
union all
select survey_year, respondent_id, variable from {{ ref('answers') }}
where variable = 'tvhours' and raw_label = '0 hours'
  and (answer_value is distinct from 0 or status <> 'answer')

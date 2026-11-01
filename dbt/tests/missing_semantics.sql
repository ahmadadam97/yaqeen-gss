with expected(raw_prefix, wanted) as (
    values ('.d:', 'dont_know'), ('.n:', 'no_answer'), ('.i:', 'inapplicable'),
           ('.y:', 'not_asked_year')
)
select a.survey_year, a.respondent_id, a.variable
from {{ ref('answers') }} a join expected e on starts_with(a.raw_label, e.raw_prefix)
where a.status <> e.wanted
union all
select survey_year, respondent_id, variable from {{ ref('answers') }}
where variable='tvhours' and raw_label='0 hours'
  and (answer_value is distinct from 0 or status <> 'answer')

select survey_year, respondent_id, variable from {{ ref('answers') }}
group by all having count(*) <> 1

with expected as (select distinct survey_year, respondent_id from {{ ref('stg_membership') }}),
actual as (select survey_year, respondent_id, count(*) as n from {{ ref('respondents') }} group by all)
select survey_year, respondent_id from expected full join actual using (survey_year, respondent_id)
where n is distinct from 1 or expected.survey_year is null

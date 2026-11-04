-- Coverage: valid answers out of all interviews by wave, ballot and split item.
select
    answers.survey_year,
    respondents.ballot,
    answers.variable,
    count(*) as interviews,
    count(*) filter (where answers.status = 'answer') as valid_n,
    round(100.0 * valid_n / count(*), 2) as valid_pct
from {{ ref('answers') }} as answers
join {{ ref('respondents') }} as respondents using (survey_year, respondent_id)
where answers.variable in ('news', 'tvhours', 'compuse', 'wwwhr', 'inttech')
group by all
order by answers.survey_year, respondents.ballot, answers.variable

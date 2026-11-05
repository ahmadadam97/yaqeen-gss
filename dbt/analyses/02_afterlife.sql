-- Q2: belief in life after death by wave, with every reason a respondent has no answer shown beside the result.
select
    survey_year,
    count(*) as interviews,
    count(postlife) as valid_n,
    count(*) filter (where postlife = 'YES') as yes_n,
    round(100.0 * count(*) filter (where postlife = 'YES') / nullif(count(postlife), 0), 2) as yes_pct,
    round(
        100.0 * sum(wtssps_value) filter (where postlife = 'YES')
        / nullif(sum(wtssps_value) filter (where postlife is not null), 0),
        2
    ) as wtssps_yes_pct,
    count(*) filter (where postlife_status = 'not_asked_year') as not_asked_year_n,
    count(*) filter (where postlife_status = 'not_asked_ballot') as not_asked_ballot_n,
    count(*) filter (where postlife_status = 'inapplicable') as inapplicable_n,
    count(*) filter (where postlife_status = 'dont_know') as dont_know_n,
    count(*) filter (where postlife_status = 'no_answer') as no_answer_n
from {{ ref('respondents') }}
group by survey_year
order by survey_year

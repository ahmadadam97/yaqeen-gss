-- Extension: belief by prayer group within each wave. The two prayer groups are exhaustive among valid answers.
with eligible as (
    select
        survey_year,
        case when pray_value in (1, 2) then 'At least daily' else 'Less than daily' end as prayer,
        postlife,
        wtssps_value,
        wtssnrps_value
    from {{ ref('respondents') }}
    where pray_value is not null
)

select
    survey_year,
    prayer,
    count(*) as prayer_n,
    count(postlife) as belief_valid_n,
    count(*) filter (where postlife = 'YES') as belief_yes_n,
    round(100 * avg((postlife = 'YES')::int), 2) as yes_pct,
    count(wtssps_value) filter (where postlife is not null) as wtssps_n,
    round(
        100 * sum(wtssps_value * (postlife = 'YES')::int)
        / nullif(sum(wtssps_value) filter (where postlife is not null), 0),
        2
    ) as wtssps_yes_pct,
    count(wtssnrps_value) filter (where postlife is not null) as wtssnrps_n,
    round(
        100 * sum(wtssnrps_value * (postlife = 'YES')::int)
        / nullif(sum(wtssnrps_value) filter (where postlife is not null), 0),
        2
    ) as wtssnrps_yes_pct
from eligible
group by survey_year, prayer
order by survey_year, prayer

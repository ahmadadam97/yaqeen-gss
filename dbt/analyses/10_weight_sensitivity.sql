-- Sensitivity for the weight choice: headline estimates under WTSSPS (primary) and WTSSNRPS.
with shares as (
    select
        'Q2 believes in life after death' as estimate,
        survey_year::varchar as subgroup,
        sum(wtssps_value) filter (where postlife = 'YES') / sum(wtssps_value) filter (where postlife is not null) as wtssps_share,
        sum(wtssnrps_value) filter (where postlife = 'YES') / sum(wtssnrps_value) filter (where postlife is not null) as wtssnrps_share,
        null::boolean as same_leader
    from {{ ref('respondents') }}
    group by survey_year

    union all

    select
        'Q5 ever worked a year, of valid answers',
        'Nonworkers',
        sum(wtssps_value) filter (where evwork = 'YES') / sum(wtssps_value) filter (where evwork is not null),
        sum(wtssnrps_value) filter (where evwork = 'YES') / sum(wtssnrps_value) filter (where evwork is not null),
        null
    from {{ ref('respondents') }}
    where is_working = false

    union all

    select
        'Q6 never reads a newspaper',
        survey_year::varchar,
        sum(wtssps_value) filter (where news = 'Never') / sum(wtssps_value) filter (where news is not null),
        sum(wtssnrps_value) filter (where news = 'Never') / sum(wtssnrps_value) filter (where news is not null),
        null
    from {{ ref('respondents') }}
    group by survey_year

    union all

    select
        'Q6 reads a newspaper daily',
        survey_year::varchar,
        sum(wtssps_value) filter (where news = 'Every day') / sum(wtssps_value) filter (where news is not null),
        sum(wtssnrps_value) filter (where news = 'Every day') / sum(wtssnrps_value) filter (where news is not null),
        null
    from {{ ref('respondents') }}
    group by survey_year

    union all

    select
        'Q3 share of the leading industry',
        degree,
        max(wtssps_weight) / sum(wtssps_weight),
        max(wtssnrps_weight) / sum(wtssnrps_weight),
        arg_max(indus10, wtssps_weight) = arg_max(indus10, wtssnrps_weight)
    from (
        select
            degree,
            indus10,
            sum(wtssps_value) as wtssps_weight,
            sum(wtssnrps_value) as wtssnrps_weight
        from {{ ref('respondents') }}
        where is_working
          and degree is not null
          and indus10 is not null
        group by all
    )
    group by degree
)

select
    estimate,
    subgroup,
    round(100 * wtssps_share, 2) as wtssps_pct,
    round(100 * wtssnrps_share, 2) as wtssnrps_pct,
    round(100 * (wtssnrps_share - wtssps_share), 2) as difference_pp,
    same_leader
from shares
order by estimate, subgroup

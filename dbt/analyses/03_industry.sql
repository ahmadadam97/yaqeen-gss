-- Q3: most common industry per degree among current workers, ranked by weighted share.
-- The runner-up is shown because a narrow lead should not be read as a clear winner.
with counts as (
    select
        degree,
        indus10 as industry,
        count(*) as n,
        sum(wtssps_value) as weight
    from {{ ref('respondents') }}
    where is_working
      and degree is not null
      and indus10 is not null
    group by all
),

ranked as (
    select
        *,
        dense_rank() over (partition by degree order by weight desc) as position,
        sum(n) over (partition by degree) as group_n,
        sum(weight) over (partition by degree) as group_weight
    from counts
)

select
    'Currently working; valid degree and industry' as cohort,
    leader.degree,
    leader.industry,
    leader.n,
    leader.group_n,
    round(100.0 * leader.weight / leader.group_weight, 2) as wtssps_pct,
    runner_up.industry as runner_up_industry,
    runner_up.n as runner_up_n,
    round(100.0 * runner_up.weight / runner_up.group_weight, 2) as runner_up_wtssps_pct
from ranked as leader
left join ranked as runner_up
    on runner_up.degree = leader.degree
    and runner_up.position = 2
where leader.position = 1
order by leader.degree, leader.industry, runner_up.industry

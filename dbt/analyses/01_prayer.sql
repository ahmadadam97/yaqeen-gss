-- Q1: prayer frequency by the religion a respondent was raised in. Percentages are within each upbringing group.
with answered as (
    select
        relig16 as upbringing,
        pray as frequency,
        pray_value,
        count(*) as n,
        sum(wtssps_value) as weight
    from {{ ref('respondents') }}
    where relig16 is not null
      and pray is not null
    group by all
)

select
    upbringing,
    frequency,
    n,
    sum(n) over upbringing_group as group_n,
    round(100.0 * n / sum(n) over upbringing_group, 2) as pct,
    round(100.0 * weight / sum(weight) over upbringing_group, 2) as wtssps_pct,
    sum(n) over upbringing_group < 50 as is_small_group
from answered
window upbringing_group as (partition by upbringing)
order by upbringing, pray_value

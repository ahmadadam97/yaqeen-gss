with counts as (
    select relig16 as upbringing, pray as frequency, pray_value, count(*) as n
    from respondents where relig16 is not null and pray is not null group by all
)
select upbringing, frequency, n, sum(n) over (partition by upbringing) as group_n,
       round(100.0*n / sum(n) over (partition by upbringing), 2) as pct
from counts order by upbringing, pray_value

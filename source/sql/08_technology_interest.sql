with groups as (
    select survey_year, inttech, count(*) as n from respondents group by all
    union all
    select null, inttech, count(*) from respondents group by inttech
), sizes as (
    select *, sum(n) over (partition by survey_year) as interviews,
           coalesce(sum(n) filter (where inttech is not null) over (partition by survey_year),0) as valid_n
    from groups
)
select coalesce(survey_year::varchar,'All waves') as wave, coalesce(inttech, 'No valid responses') as response,
       case when inttech is null then 0 else n end as n, valid_n, interviews,
       round(100.0*n/nullif(valid_n,0),2) as pct_of_valid,
       round(100.0*valid_n/interviews,2) as valid_coverage_pct
from sizes where inttech is not null or valid_n=0 order by survey_year nulls last, response

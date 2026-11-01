with membership as (
    select survey_year, respondent_id,
           bool_or(filename='yaqeen_cut_a_2014_2016.json') as in_a,
           bool_or(filename='yaqeen_cut_b_2016_2018.json') as in_b
    from stg_membership group by all
), counts as (
    select count(*) filter (where in_a) as a, count(*) filter (where in_b) as b,
           count(*) filter (where in_a and in_b) as shared, count(*) filter (where in_a or in_b) as distinct_n
    from membership
)
select *, round(100.0*shared/nullif(a,0),2) as pct_a, round(100.0*shared/nullif(b,0),2) as pct_b
from counts

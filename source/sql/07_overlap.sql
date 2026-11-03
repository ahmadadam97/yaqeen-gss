with membership as (
    select survey_year, respondent_id,
           bool_or(filename='yaqeen_cut_a_2014_2016.json') as in_a,
           bool_or(filename='yaqeen_cut_b_2016_2018.json') as in_b
    from stg_membership
    where filename in ('yaqeen_cut_a_2014_2016.json','yaqeen_cut_b_2016_2018.json')
    group by all
), counts as (
    select count(*) filter (where in_a) as a, count(*) filter (where in_b) as b,
           count(*) filter (where in_a and in_b) as shared, count(*) filter (where in_a or in_b) as distinct_n
    from membership
), grain as (
    select count(*) as analysis_rows, count(distinct (survey_year,respondent_id)) as distinct_interview_keys,
           count(distinct respondent_id) as distinct_ids_alone
    from respondents r
    where exists (
        select 1 from membership m
        where m.survey_year=r.survey_year and m.respondent_id=r.respondent_id
    )
)
select *, round(100.0*shared/nullif(a,0),2) as pct_a, round(100.0*shared/nullif(b,0),2) as pct_b,
       analysis_rows-distinct_interview_keys as duplicate_analysis_rows,
       distinct_interview_keys-distinct_ids_alone as interviews_lost_using_id_alone
from counts cross join grain

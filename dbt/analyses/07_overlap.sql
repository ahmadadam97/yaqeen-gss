-- Overlap audit for the two cuts named in extract_cuts, and proof that the analysis table counts each interview once.
with membership as (
    select
        stg_membership.survey_year,
        stg_membership.respondent_id,
        bool_or(extract_cuts.cut = 'A') as in_a,
        bool_or(extract_cuts.cut = 'B') as in_b
    from {{ ref('stg_membership') }} as stg_membership
    join {{ ref('extract_cuts') }} as extract_cuts using (filename)
    group by all
),

counts as (
    select
        count(*) filter (where in_a) as cut_a_n,
        count(*) filter (where in_b) as cut_b_n,
        count(*) filter (where in_a and in_b) as shared_n,
        count(*) filter (where in_a or in_b) as distinct_n
    from membership
),

grain as (
    select
        count(*) as analysis_rows,
        count(distinct (survey_year, respondent_id)) as distinct_interview_keys,
        count(distinct respondent_id) as distinct_ids_alone
    from {{ ref('respondents') }} as respondents
    where exists (
        select 1
        from membership
        where membership.survey_year = respondents.survey_year
          and membership.respondent_id = respondents.respondent_id
    )
)

select
    *,
    round(100.0 * shared_n / nullif(cut_a_n, 0), 2) as shared_of_cut_a_pct,
    round(100.0 * shared_n / nullif(cut_b_n, 0), 2) as shared_of_cut_b_pct,
    analysis_rows - distinct_interview_keys as duplicate_analysis_rows,
    distinct_interview_keys - distinct_ids_alone as interviews_lost_using_id_alone
from counts
cross join grain

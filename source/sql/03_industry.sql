with counts as (
    select degree, indus10 as industry, count(*) as n
    from respondents where is_working and degree is not null and indus10 is not null group by all
), ranked as (
    select *, dense_rank() over (partition by degree order by n desc) as position,
           sum(n) over (partition by degree) as group_n from counts
)
select 'Currently working; valid degree and industry' as cohort,
       degree, industry, n, group_n from ranked where position=1 order by degree, industry

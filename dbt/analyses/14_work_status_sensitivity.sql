-- Sensitivity for Q3-Q5: reclassify temporarily absent workers as not working.
with classified as (
    select
        respondents.*,
        definitions.definition,
        case
            when definitions.definition = 'Standard: codes 1-3' then wrkstat_value between 1 and 3
            else wrkstat_value between 1 and 2
        end as working
    from {{ ref('respondents') }} as respondents
    cross join (values ('Standard: codes 1-3'), ('Alternative: codes 1-2')) as definitions(definition)
),

industry as (
    select
        definition,
        degree as subgroup,
        indus10 as detail,
        count(*) as n,
        sum(count(*)) over (partition by definition, degree) as denominator,
        dense_rank() over (partition by definition, degree order by count(*) desc) as position
    from classified
    where working
      and degree is not null
      and indus10 is not null
    group by definition, degree, indus10
),

tv as (
    select
        definition,
        satjob as subgroup,
        count(*) as n,
        avg(tvhours_value) as value
    from classified
    where working
      and satjob is not null
      and tvhours_value is not null
    group by all
),

work_history as (
    select
        definition,
        count(*) as n,
        count(evwork) as denominator,
        count(*) filter (where evwork = 'YES') as yes_n,
        count(*) - count(evwork) as missing_n
    from classified
    where working = false
    group by definition
)

select 'Q3' as question, definition, subgroup, detail, n, denominator, round(100.0 * n / denominator, 2) as value
from industry
where position = 1

union all

select 'Q4', definition, subgroup, 'mean TV hours/day', n, n, round(value, 2)
from tv

union all

select 'Q5', definition, 'Observed yes', 'nonworkers / valid answers', n, denominator,
    round(100.0 * yes_n / nullif(denominator, 0), 2)
from work_history

union all

select 'Q5', definition, 'Lower bound', 'all missing assigned no', n, denominator,
    round(100.0 * yes_n / nullif(n, 0), 2)
from work_history

union all

select 'Q5', definition, 'Upper bound', 'all missing assigned yes', n, denominator,
    round(100.0 * (yes_n + missing_n) / nullif(n, 0), 2)
from work_history

order by question, definition, subgroup, detail

-- A variable that loses its answers in one wave must fail, not publish an empty estimate for that wave.
with coverage as (
    select
        survey_year,
        variable,
        100.0 * count(*) filter (where status = 'answer') / count(*) as valid_pct
    from {{ ref('answers') }}
    group by survey_year, variable
)

select coverage.survey_year, coverage.variable, coverage.valid_pct, variables.min_valid_pct
from coverage
join {{ ref('variables') }} as variables using (variable)
where coverage.valid_pct < variables.min_valid_pct

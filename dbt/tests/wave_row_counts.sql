-- A wave must hold exactly the interviews NORC released, so a truncated export fails even when its manifest was resealed.
with observed as (
    select survey_year, count(*) as interviews
    from {{ ref('respondents') }}
    group by survey_year
)

select survey_year, expected.expected_interviews, observed.interviews
from {{ ref('wave_expectations') }} as expected
full join observed using (survey_year)
where expected.expected_interviews is distinct from observed.interviews

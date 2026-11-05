with raw_answers as (
    select * from {{ ref('stg_answers') }}
),

interviews as (
    select distinct survey_year, respondent_id
    from {{ ref('stg_membership') }}
),

lookup as (
    -- Two uncodeable industry codes have the same label. Neither identifies an industry.
    select variable, label, kind, case when count(*) = 1 then min(source_code) end as source_code
    from {{ ref('codebook') }}
    group by all
),

interview_context as (
    select
        raw_answers.survey_year,
        raw_answers.respondent_id,
        max(lookup.source_code) filter (where raw_answers.variable = 'ballot') as ballot_code,
        max(lookup.source_code) filter (where raw_answers.variable = 'form') as form_code
    from raw_answers
    left join lookup on lookup.variable = raw_answers.variable and lookup.label = raw_answers.raw_label
    group by raw_answers.survey_year, raw_answers.respondent_id
),

decoded as (
    select
        interviews.*,
        eligibility.is_eligible,
        variables.variable,
        raw_answers.raw_label,
        lookup.source_code,
        lookup.kind as code_kind,
        variables.kind,
        variables.min_value,
        variables.max_value,
        variables.reviewed_years,
        raw_answers.variable is not null as present,
        coalesce(lookup.source_code::double, try_cast(raw_answers.raw_label as double)) as candidate_value
    from interviews
    cross join {{ ref('variables') }} as variables
    left join raw_answers using (survey_year, respondent_id, variable)
    left join lookup on lookup.variable = variables.variable and lookup.label = raw_answers.raw_label
    left join interview_context using (survey_year, respondent_id)
    left join {{ ref('eligibility') }} as eligibility
        on eligibility.variable = variables.variable
        and eligibility.survey_year = interviews.survey_year
        and eligibility.ballot_code = interview_context.ballot_code
        and eligibility.form_code = interview_context.form_code
),

classified as (
    select
        *,
        case
            when not list_contains(string_split(reviewed_years, '|'), survey_year::varchar) then 'unreviewed_year'
            when not present then 'absent_field'
            when raw_label is null then 'unspecified_missing'
            when code_kind = 'inapplicable' and is_eligible is false then 'not_asked_ballot'
            when code_kind is not null and code_kind <> 'answer' then code_kind
            when kind = 'category' then coalesce(code_kind, 'unknown_code')
            when not isfinite(candidate_value) or candidate_value is null
                or candidate_value < min_value or candidate_value > max_value
                or (kind = 'integer' and candidate_value <> trunc(candidate_value))
                or (kind = 'weight' and candidate_value <= 0) then 'invalid_number'
            else 'answer'
        end as status
    from decoded
)

select
    survey_year,
    respondent_id,
    variable,
    raw_label,
    source_code,
    code_kind as source_status,
    is_eligible,
    status,
    case when status = 'answer' then raw_label end as answer_label,
    case when status = 'answer' then candidate_value end as answer_value
from classified

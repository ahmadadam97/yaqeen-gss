with raw_answers as (
    select distinct survey_year, respondent_id, field.key as variable,
           json_extract_string(field.value, '$') as raw_label
    from {{ ref('stg_membership') }}
    join {{ source('raw', 'records') }} using (filename, ordinal),
    lateral json_each(payload) field
    where field.key not in ('year', 'id_')
), interviews as (
    select distinct survey_year, respondent_id from {{ ref('stg_membership') }}
), lookup as (
    -- Two uncodeable industry codes have the same label. Neither identifies an industry.
    select variable, label, kind, case when count(*) = 1 then min(source_code) end as source_code
    from {{ ref('codebook') }} group by all
), decoded as (
    select i.*, v.variable, r.raw_label, c.source_code, c.kind as code_kind, v.kind,
           v.min_value, v.max_value, v.reviewed_years,
           r.variable is not null as present,
           coalesce(c.source_code::double, try_cast(r.raw_label as double)) as candidate_value
    from interviews i cross join {{ ref('variables') }} v
    left join raw_answers r using (survey_year, respondent_id, variable)
    left join lookup c on c.variable=v.variable and c.label=r.raw_label
), classified as (
    select *, case
        when not list_contains(string_split(reviewed_years, '|'), survey_year::varchar) then 'unreviewed_year'
        when not present then 'absent_field'
        when raw_label is null then 'unspecified_missing'
        when code_kind is not null and code_kind <> 'answer' then code_kind
        when kind = 'category' then coalesce(code_kind, 'unknown_code')
        when not isfinite(candidate_value) or candidate_value is null
          or candidate_value < min_value or candidate_value > max_value
          or (kind = 'integer' and candidate_value <> trunc(candidate_value))
          or (kind = 'weight' and candidate_value <= 0) then 'invalid_number'
        else 'answer' end as status
    from decoded
)
select survey_year, respondent_id, variable, raw_label, source_code, status,
       case when status='answer' then raw_label end as answer_label,
       case when status='answer' then candidate_value end as answer_value
from classified

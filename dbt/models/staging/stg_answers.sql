-- Unpacks each received JSON field. An interview in both cuts agrees field for field (the loader checks), so distinct gives one row.
select distinct
    membership.survey_year,
    membership.respondent_id,
    field.key as variable,
    json_extract_string(field.value, '$') as raw_label
from {{ ref('stg_membership') }} as membership
join {{ source('raw', 'records') }} as records using (filename, ordinal),
lateral json_each(records.payload) as field
where field.key not in ('year', 'id_')

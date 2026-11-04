select
    filename,
    ordinal,
    (payload->>'year')::integer as survey_year,
    (payload->>'id_')::integer as respondent_id
from {{ source('raw', 'records') }}

select variable from {{ ref('variables') }} group by variable having count(*) <> 1

union all

select variable from {{ ref('eligibility') }}
group by variable, survey_year, ballot_code, form_code having count(*) <> 1

union all

select variable from {{ ref('answers') }}
where status = 'not_asked_ballot' and (source_status <> 'inapplicable' or is_eligible is distinct from false)

union all

-- A renamed extract must fail here, not produce a silent zero in the overlap audit.
select filename from {{ ref('extract_cuts') }}
where filename not in (select filename from {{ ref('stg_membership') }})

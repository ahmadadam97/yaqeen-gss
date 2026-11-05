select variable from {{ ref('variables') }} group by variable having count(*) <> 1

union all

select variable from {{ ref('eligibility') }}
group by variable, survey_year, ballot_code, form_code having count(*) <> 1

union all

-- A skip on a ballot that never had the question is not asked, which is different from routed out.
select variable from {{ ref('answers') }}
where source_status = 'inapplicable' and is_eligible is false and status <> 'not_asked_ballot'

union all

-- A renamed extract must fail here, not produce a silent zero in the overlap audit.
select filename from {{ ref('extract_cuts') }}
where filename not in (select filename from {{ ref('stg_membership') }})

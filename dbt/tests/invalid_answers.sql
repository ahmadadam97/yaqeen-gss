select * from {{ ref('answers') }}
where status in ('unknown_code','invalid_number','unreviewed_year')
   or (status <> 'answer' and (answer_value is not null or answer_label is not null))
   or (status = 'answer' and (answer_value is null or answer_label is null))

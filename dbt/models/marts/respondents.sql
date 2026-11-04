-- depends_on: {{ ref('variables') }}
{% set columns = run_query('select variable, wide_label, wide_value, wide_status from ' ~ ref('variables') ~ ' order by variable') if execute else [] %}
with pivoted as (
    select
        survey_year,
        respondent_id,
    {% for variable, label, value, status in columns %}
      {% if label %}
        max(answer_label) filter (where variable = '{{ variable }}') as {{ variable }},
      {% endif %}
      {% if value %}
        max(answer_value) filter (where variable = '{{ variable }}') as {{ variable }}_value,
      {% endif %}
      {% if status %}
        max(status) filter (where variable = '{{ variable }}') as {{ variable }}_status,
      {% endif %}
    {% endfor %}
        count(*) as catalogued_items
    from {{ ref('answers') }}
    group by survey_year, respondent_id
)

select
    pivoted.*,
    work_status.is_working,
    work_status.ever_work_eligible,
    work_status.satjob_eligible,
    pivoted.wwwhr_value + pivoted.wwwmin_value / 60.0 as web_hours_weekly
from pivoted
left join {{ ref('work_status') }} as work_status on pivoted.wrkstat_value = work_status.source_code

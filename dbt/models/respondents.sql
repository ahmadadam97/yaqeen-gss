-- depends_on: {{ ref('variables') }}
{% set columns = run_query('select variable, wide_label, wide_value, wide_status from ' ~ ref('variables') ~ ' order by variable') if execute else [] %}
with pivoted as (
    select survey_year, respondent_id,
    {% for variable, label, value, status in columns %}
      {% if label %}
        max(answer_label) filter (where variable='{{ variable }}') as {{ variable }},
      {% endif %}
      {% if value %}
        max(answer_value) filter (where variable='{{ variable }}') as {{ variable }}_value,
      {% endif %}
      {% if status %}
        max(status) filter (where variable='{{ variable }}') as {{ variable }}_status,
      {% endif %}
    {% endfor %}
        count(*) as catalogued_items
    from {{ ref('answers') }} group by survey_year, respondent_id
)
select p.*, s.is_working, s.ever_work_eligible,
       wwwhr_value + wwwmin_value / 60.0 as web_hours_weekly
from pivoted p left join {{ ref('work_status') }} s on p.wrkstat_value=s.source_code

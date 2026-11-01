with pivoted as (
    select survey_year, respondent_id,
    {% for var in ['wrkstat','evwork','degree','indus10','satjob','postlife','pray','relig16','relig','attend','reliten','news','inttech','sex','region','form','mode','ballot'] %}
        max(answer_label) filter (where variable='{{ var }}') as {{ var }},
    {% endfor %}
    {% for var in ['age','educ','tvhours','wwwhr','wwwmin','wtssps','wtssnrps','wrkstat','pray'] %}
        max(answer_value) filter (where variable='{{ var }}') as {{ var }}_value,
    {% endfor %}
        max(status) filter (where variable='postlife') as postlife_status
    from {{ ref('answers') }}
    group by survey_year, respondent_id
)
select *, wrkstat_value between 1 and 3 as is_working,
       wrkstat_value between 5 and 8 as ever_work_eligible,
       wwwhr_value + wwwmin_value / 60.0 as web_hours_weekly
from pivoted

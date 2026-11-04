-- Sensitivity for query 11. Assign zero only when the respondent explicitly denied non-email web use
-- and both duration fields were skipped by routing. An ordinary missing answer stays unknown.
with web as (
    select
        respondents.age_value,
        respondents.web_hours_weekly,
        web_use.answer_label = 'NO'
            and hours.status = 'inapplicable'
            and minutes.status = 'inapplicable' as is_explicit_nonuser
    from {{ ref('respondents') }} as respondents
    join {{ ref('answers') }} as web_use using (survey_year, respondent_id)
    join {{ ref('answers') }} as hours using (survey_year, respondent_id)
    join {{ ref('answers') }} as minutes using (survey_year, respondent_id)
    where respondents.survey_year = 2018
      and respondents.age_value is not null
      and respondents.news is not null
      and web_use.variable = 'usewww'
      and hours.variable = 'wwwhr'
      and minutes.variable = 'wwwmin'
)

select
    case
        when age_value < 35 then '18-34'
        when age_value < 55 then '35-54'
        else '55+'
    end as age_band,
    count(*) filter (where is_explicit_nonuser and web_hours_weekly is null) as added_n,
    median(coalesce(web_hours_weekly, case when is_explicit_nonuser then 0 end)) as median_hours
from web
group by age_band
order by age_band

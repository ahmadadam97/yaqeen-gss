-- Keep the published Q11 complete-case result. For this alternative only, assign
-- zero when the respondent explicitly denied non-email web use and both duration
-- fields were skipped by routing. An ordinary missing answer stays unknown.
with web as (
    select r.age_value, r.web_hours_weekly,
           u.answer_label = 'NO' and h.status = 'inapplicable'
               and m.status = 'inapplicable' as explicit_nonuser
    from respondents r
    join answers u using (survey_year, respondent_id)
    join answers h using (survey_year, respondent_id)
    join answers m using (survey_year, respondent_id)
    where r.survey_year = 2018 and r.age_value is not null and r.news is not null
      and u.variable = 'usewww' and h.variable = 'wwwhr' and m.variable = 'wwwmin'
)
select case when age_value < 35 then '18-34' when age_value < 55 then '35-54'
            else '55+' end as age_band,
       count(*) filter (where explicit_nonuser and web_hours_weekly is null) as added_n,
       median(coalesce(web_hours_weekly, case when explicit_nonuser then 0 end)) as median_hours
from web group by age_band order by age_band

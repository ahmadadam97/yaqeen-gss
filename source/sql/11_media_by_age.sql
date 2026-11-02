-- Both measures use the same people within a row. Include zero-hour web answers.
with eligible as (
    select survey_year,
           case when age_value < 35 then '18-34' when age_value < 55 then '35-54'
                else '55+' end as age_band,
           news, web_hours_weekly, news is not null and web_hours_weekly is not null as paired
    from respondents where age_value is not null
)
select survey_year, age_band, count(*) as known_age_n, count(news) as news_n,
       count(web_hours_weekly) as web_n, count(*) filter (where paired) as paired_n,
       round(100 * avg(paired::int), 2) as paired_coverage_pct,
       round(100 * avg((news = 'Every day')::int) filter (where paired), 2) as daily_news_pct,
       median(web_hours_weekly) filter (where paired) as median_web_hours_per_week
from eligible group by survey_year, age_band order by survey_year, age_band

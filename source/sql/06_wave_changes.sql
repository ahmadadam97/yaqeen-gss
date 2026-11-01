with waves as (
    select survey_year, count(news) as news_n, count(tvhours_value) as tv_n,
           100.0*count(*) filter (where news='Every day') / nullif(count(news),0) as daily_news_pct,
           avg(tvhours_value) as mean_tv_hours from respondents group by survey_year
)
select survey_year, news_n, tv_n, round(daily_news_pct,2) as daily_news_pct,
       round(daily_news_pct-lag(daily_news_pct) over w,2) as news_change_pp,
       round(mean_tv_hours,2) as mean_tv_hours,
       round(mean_tv_hours-lag(mean_tv_hours) over w,2) as tv_change_hours
from waves window w as (order by survey_year) order by survey_year

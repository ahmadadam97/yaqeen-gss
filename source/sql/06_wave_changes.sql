-- Unweighted independent-sample SEs. Survey design and multiple comparisons are not adjusted.
with waves as (
    select survey_year, count(news) as news_n, count(tvhours_value) as tv_n,
           avg((news='Every day')::int) as p, avg(tvhours_value) as tv,
           var_samp(tvhours_value)/nullif(count(tvhours_value),0) as tv_var_mean
    from respondents group by survey_year
), deltas as (
    select *, 100*(p-lag(p) over w) as news_change, tv-lag(tv) over w as tv_change,
           100*sqrt(p*(1-p)/news_n + lag(p*(1-p)/news_n) over w) as news_se,
           sqrt(tv_var_mean + lag(tv_var_mean) over w) as tv_se
    from waves window w as (order by survey_year)
)
select survey_year, news_n, tv_n, round(100*p,2) as daily_news_pct,
       round(news_change,2) as news_change_pp, round(news_se,2) as news_change_se_pp,
       round(news_change/nullif(news_se,0),2) as news_z,
       round(tv,2) as mean_tv_hours, round(tv_change,2) as tv_change_hours,
       round(tv_se,3) as tv_change_se_hours, round(tv_change/nullif(tv_se,0),2) as tv_z
from deltas order by survey_year

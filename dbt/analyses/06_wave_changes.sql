-- Q6: newspaper reading and TV viewing from one wave to the next. WTSSPS columns are the primary estimate.
-- Standard errors treat waves as independent. Weighted ones use Kish effective n, which allows for unequal weights
-- but not for strata or clusters (VSTRAT and VPSU are not in the extracts). Read z values as approximate.
with waves as (
    select
        survey_year,
        count(news) as news_n,
        count(tvhours_value) as tv_n,
        avg((news = 'Every day')::int) as daily_news,
        avg((news = 'Never')::int) as never_news,
        avg(tvhours_value) as tv_mean,
        var_samp(tvhours_value) / nullif(count(tvhours_value), 0) as tv_mean_variance,
        sum(wtssps_value) filter (where news is not null) as news_weight,
        sum(wtssps_value ^ 2) filter (where news is not null) as news_weight_squared,
        sum(wtssps_value) filter (where news = 'Every day') as daily_news_weight,
        sum(wtssps_value) filter (where news = 'Never') as never_news_weight,
        sum(wtssps_value) filter (where tvhours_value is not null) as tv_weight,
        sum(wtssps_value ^ 2) filter (where tvhours_value is not null) as tv_weight_squared,
        sum(wtssps_value * tvhours_value) as tv_weighted_hours,
        sum(wtssps_value * tvhours_value ^ 2) as tv_weighted_hours_squared
    from {{ ref('respondents') }}
    group by survey_year
),

estimates as (
    select
        *,
        daily_news_weight / news_weight as wtssps_daily_news,
        never_news_weight / news_weight as wtssps_never_news,
        tv_weighted_hours / tv_weight as wtssps_tv_mean,
        (daily_news_weight / news_weight) * (1 - daily_news_weight / news_weight)
            / (news_weight ^ 2 / news_weight_squared) as wtssps_daily_news_variance,
        (never_news_weight / news_weight) * (1 - never_news_weight / news_weight)
            / (news_weight ^ 2 / news_weight_squared) as wtssps_never_news_variance,
        (tv_weighted_hours_squared / tv_weight - (tv_weighted_hours / tv_weight) ^ 2)
            / (tv_weight ^ 2 / tv_weight_squared) as wtssps_tv_mean_variance
    from waves
),

changes as (
    select
        *,
        100 * (daily_news - lag(daily_news) over wave_order) as news_change,
        100 * sqrt(
            daily_news * (1 - daily_news) / news_n
            + lag(daily_news * (1 - daily_news) / news_n) over wave_order
        ) as news_se,
        tv_mean - lag(tv_mean) over wave_order as tv_change,
        sqrt(tv_mean_variance + lag(tv_mean_variance) over wave_order) as tv_se,
        100 * (wtssps_daily_news - lag(wtssps_daily_news) over wave_order) as wtssps_news_change,
        100 * sqrt(wtssps_daily_news_variance + lag(wtssps_daily_news_variance) over wave_order) as wtssps_news_se,
        100 * (wtssps_never_news - lag(wtssps_never_news) over wave_order) as wtssps_never_change,
        100 * sqrt(wtssps_never_news_variance + lag(wtssps_never_news_variance) over wave_order) as wtssps_never_se,
        wtssps_tv_mean - lag(wtssps_tv_mean) over wave_order as wtssps_tv_change,
        sqrt(wtssps_tv_mean_variance + lag(wtssps_tv_mean_variance) over wave_order) as wtssps_tv_se,
        100 * (wtssps_daily_news - first_value(wtssps_daily_news) over wave_order) as wtssps_news_since_first,
        100 * sqrt(wtssps_daily_news_variance + first_value(wtssps_daily_news_variance) over wave_order) as wtssps_news_since_first_se
    from estimates
    window wave_order as (order by survey_year)
)

select
    survey_year,
    news_n,
    tv_n,
    round(100 * daily_news, 2) as daily_news_pct,
    round(news_change, 2) as news_change_pp,
    round(news_se, 2) as news_change_se_pp,
    round(news_change / nullif(news_se, 0), 2) as news_z,
    round(100 * never_news, 2) as never_news_pct,
    round(tv_mean, 2) as mean_tv_hours,
    round(tv_change, 2) as tv_change_hours,
    round(tv_se, 3) as tv_change_se_hours,
    round(tv_change / nullif(tv_se, 0), 2) as tv_z,
    round(100 * wtssps_daily_news, 2) as wtssps_daily_news_pct,
    round(wtssps_news_change, 2) as wtssps_news_change_pp,
    round(wtssps_news_se, 2) as wtssps_news_change_se_pp,
    round(wtssps_news_change / nullif(wtssps_news_se, 0), 2) as wtssps_news_z,
    round(100 * wtssps_never_news, 2) as wtssps_never_news_pct,
    round(wtssps_never_change, 2) as wtssps_never_change_pp,
    round(wtssps_never_change / nullif(wtssps_never_se, 0), 2) as wtssps_never_z,
    round(wtssps_tv_mean, 2) as wtssps_mean_tv_hours,
    round(wtssps_tv_change, 2) as wtssps_tv_change_hours,
    round(wtssps_tv_se, 3) as wtssps_tv_change_se_hours,
    round(wtssps_tv_change / nullif(wtssps_tv_se, 0), 2) as wtssps_tv_z,
    round(wtssps_news_since_first, 2) as wtssps_news_since_first_pp,
    round(wtssps_news_since_first / nullif(wtssps_news_since_first_se, 0), 2) as wtssps_news_since_first_z
from changes
order by survey_year

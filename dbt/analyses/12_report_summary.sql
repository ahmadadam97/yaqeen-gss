-- Worker and satisfaction counts quoted in the report.
select
    (select count(*) from {{ ref('respondents') }} where wrkstat_value = 3) as temporarily_absent_n,
    count(*) as workers_n,
    count(satjob) as satisfaction_valid_n,
    count(*) filter (where satjob in ('Very satisfied', 'Moderately satisfied')) as satisfied_n,
    (
        select count(*)
        from (
            select satjob
            from {{ ref('respondents') }}
            where is_working
              and satjob is not null
              and tvhours_value is not null
            group by satjob
            having median(tvhours_value) <> 2
        )
    ) as groups_with_median_not_two
from {{ ref('respondents') }}
where is_working

-- WTSSPS is scaled to the sample, so it sums to the interviews in each of these waves. One bad weight breaks that.
select survey_year, count(*) as interviews, sum(wtssps_value) as total_weight
from {{ ref('respondents') }}
group by survey_year
having sum(wtssps_value) is null or abs(sum(wtssps_value) - count(*)) > 1

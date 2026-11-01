select survey_year, count(*) as interviews, count(postlife) as valid_n,
       count(*) filter (where postlife='YES') as yes_n,
       round(100.0 * count(*) filter (where postlife='YES') / nullif(count(postlife),0), 2) as yes_pct,
       count(*) filter (where postlife_status='not_asked_year') as not_asked_year_n,
       count(*) filter (where postlife_status='inapplicable') as inapplicable_n,
       count(*) filter (where postlife_status='dont_know') as dont_know_n,
       count(*) filter (where postlife_status='no_answer') as no_answer_n
from respondents group by survey_year order by survey_year

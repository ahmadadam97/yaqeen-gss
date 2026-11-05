"""Unweighted exploratory rank tests on Q4's complete-case cohort."""
from collections import defaultdict

from scipy.stats import kruskal, spearmanr


def summarize(con):
    rows = con.execute("""select satjob_value, tvhours_value
        from marts.respondents
        where is_working and satjob_value is not null and tvhours_value is not null
        order by survey_year, respondent_id""").fetchall()
    groups = defaultdict(list)
    for code, hours in rows:
        groups[code].append(hours)
    result = dict(n=len(rows), satisfaction_groups=len(groups), rho=None, spearman_p=None,
                  kw_h=None, kw_p=None, scoring="higher rank = more satisfied",
                  inference="unweighted; assumes independent observations")
    if len(groups) < 2 or len({hours for _, hours in rows}) < 2:
        return result
    # NORC codes satisfied to dissatisfied, so reverse the sign for this stated direction.
    rho, sp = spearmanr([-code for code, _ in rows], [hours for _, hours in rows])
    h, kp = kruskal(*groups.values())
    result.update(rho=round(float(rho),5), spearman_p=round(float(sp),5),
                  kw_h=round(float(h),5), kw_p=round(float(kp),5))
    return result

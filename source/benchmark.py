"""Compare the SQL queries and retain actual plans for the slowest baseline."""
import os
import statistics
import time

import duckdb
from load import ROOT
from snapshot import current_run


def measure(con, sql):
    timings = []
    for run in range(4):  # one warmup, three measured executions
        start = time.perf_counter()
        rows = con.execute(sql).fetchall()
        if run:
            timings.append(1000 * (time.perf_counter() - start))
    return statistics.median(timings), rows


if __name__ == "__main__":
    run, _ = current_run()
    db = str(run / "gss.duckdb")
    with duckdb.connect(db, read_only=True) as con:
        con.execute("set threads=1")
        model = run / "dbt/compiled/gss/models/respondents.sql"
        con.execute("create temp view baseline_interviews as " + model.read_text(encoding="utf8"))
        keys = run / "dbt/compiled/gss/models/stg_membership.sql"
        con.execute("create temp view baseline_membership as " + keys.read_text(encoding="utf8"))
        results = []
        for f in sorted((ROOT / "source/sql").glob("*.sql")):
            sql = f.read_text(encoding="utf8")
            before = sql.replace("from stg_membership", "from baseline_membership")
            if not f.name.startswith("07"):
                before = before.replace("from respondents", "from baseline_interviews").replace(
                    "join respondents", "join baseline_interviews")
            ms, rows = measure(con, before)
            assert rows == con.execute(sql).fetchall(), f.name
            results.append((ms, f.name, before, sql, rows))
        ms, name, before, after, rows = max(results, key=lambda result: result[0])
        after_ms, after_rows = measure(con, after)
        assert rows == after_rows
        out = ROOT / "report"
        lines = [f"Slowest baseline: {name}", "Single thread, median of 3 warm runs; durations include fetching rows.",
                 "Baseline ms: " + ", ".join(f"{n} {t:.2f}" for t,n,*_ in results),
                 f"Before: {ms:.2f} ms; after: {after_ms:.2f} ms; equal result rows: {len(rows)}."]
        for label, sql in (("BEFORE",before),("AFTER",after)):
            lines.extend([label, con.execute("explain analyze " + sql).fetchone()[1]])
        plan_text = "\n".join(part.rstrip() for part in "\n".join(lines).splitlines()) + "\n"
        (out / "query-plans.txt").write_text(plan_text, encoding="utf8")
        print("\n".join(lines[:4]))

"""Measure query reads and the incremental cost of each table over its view."""
import json
import math
import statistics
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
from load import ROOT
from snapshot import current_run, build_root, definition_digest


def measure(con, sql):
    timings = []
    for run in range(4):
        start = time.perf_counter()
        rows = con.execute(sql).fetchall()
        if run:
            timings.append(1000 * (time.perf_counter() - start))
    return statistics.median(timings), rows


def break_even_reads(build_ms, view_ms, table_ms):
    saving = view_ms - table_ms
    return math.ceil(build_ms / saving) if saving > 0 else None


def materialization_cost(database, sql, scratch):
    """Three fresh isolated files; dependencies stay in the read-only publication."""
    durations, storage = [], []
    for index in range(3):
        file = scratch / f"trial-{index}.duckdb"
        with duckdb.connect(str(file)) as con:
            con.execute("set threads=1")
            source = str(database).replace("'", "''")
            con.execute(f"attach '{source}' as gss (read_only)")
            con.execute("create view measured_model as " + sql)
            con.execute("checkpoint")
            view_bytes = file.stat().st_size
            con.execute("drop view measured_model")
            con.execute("checkpoint")
            start = time.perf_counter()
            con.execute("create table measured_model as " + sql)
            con.execute("checkpoint")
            durations.append(1000 * (time.perf_counter() - start))
            row_count = con.execute("select count(*) from measured_model").fetchone()[0]
        storage.append(file.stat().st_size - view_bytes)
    return dict(build_ms=statistics.median(durations),
                incremental_storage_bytes=int(statistics.median(storage)), rows=row_count)


def main():
    run, manifest = current_run()
    database = run / "gss.duckdb"
    compiled = run / "dbt/compiled/gss"
    model_sql = {name: (compiled / "models" / layer / f"{name}.sql").read_text(encoding="utf8")
                 for name, layer in (("stg_membership", "staging"), ("answers", "marts"), ("respondents", "marts"))}
    with duckdb.connect(str(database), read_only=True) as con:
        con.execute("set threads=1")
        con.execute("create temp view baseline_interviews as " + model_sql["respondents"])
        results = []
        for path in sorted((ROOT / "dbt/analyses").glob("*.sql")):
            if definition_digest(path) != manifest["definitions"].get(path.relative_to(ROOT).as_posix()):
                raise ValueError(f"Query changed since publication: {path.name}; rebuild the pipeline")
            sql = (compiled / "analyses" / path.name).read_text(encoding="utf8")
            before = sql.replace('"gss"."marts"."respondents"', "baseline_interviews")
            ms, rows = measure(con, before)
            assert rows == con.execute(sql).fetchall(), path.name
            results.append((ms, path.name, before, sql, rows))
        ms, name, before, after, rows = max(results, key=lambda result: result[0])
        after_ms, after_rows = measure(con, after)
        assert rows == after_rows
        plans = {label: con.execute("explain analyze " + sql).fetchone()[1]
                 for label, sql in (("BEFORE", before), ("AFTER", after))}
    costs = {}
    with TemporaryDirectory(prefix="benchmark-", dir=build_root()) as temp:
        for model, sql in model_sql.items():
            scratch = Path(temp) / model
            scratch.mkdir()
            costs[model] = materialization_cost(database, sql, scratch)
    changed_model = "respondents"
    cost = costs[changed_model]
    reads = break_even_reads(cost["build_ms"], ms, after_ms)
    evidence = dict(run_id=manifest["run_id"], inputs=manifest["inputs"],
                    model_hashes={name:value for name,value in manifest["definitions"].items() if name.startswith("dbt/") and not name.startswith("dbt/analyses/")},
                    query_hashes={name:value for name,value in manifest["definitions"].items() if name.startswith("dbt/analyses/")},
                    slowest_query=name, changed_model=changed_model, before_ms=ms, after_ms=after_ms,
                    equal_result_rows=len(rows), break_even_reads=reads, materialization=costs,
                    method="One thread. Read medians: 3 warm runs after 1 warm-up. Build medians: 3 fresh isolated databases, CTAS plus checkpoint. Dependencies remain materialized in the read-only source. Storage is the incremental file size over the same model as a view. Excludes dbt process startup, upstream storage, and monetary storage cost.")
    lines = [f"Slowest baseline: {name}", evidence["method"],
             "Baseline ms: " + ", ".join(f"{n} {t:.2f}" for t,n,*_ in results),
             f"Before: {ms:.2f} ms; after: {after_ms:.2f} ms; equal result rows: {len(rows)}."]
    for model, value in costs.items():
        lines.append(f"{model}: build {value['build_ms']:.2f} ms; incremental storage {value['incremental_storage_bytes']} bytes; rows {value['rows']}.")
    lines.append(f"Break-even for {changed_model} and {name}: {reads} repeated reads per rebuild.")
    for label, plan in plans.items():
        lines.extend([label, plan])
    out = ROOT / "report"
    (out / "materialization-costs.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf8")
    (out / "query-plans.txt").write_text("\n".join(line.rstrip() for line in "\n".join(lines).splitlines()) + "\n", encoding="utf8")
    print("\n".join(lines[:8]))


if __name__ == "__main__":
    main()

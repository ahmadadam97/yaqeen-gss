"""Measure the load and the dbt build at larger shapes, using synthetic rows copied from the real records.

The wave row-count, weight-total and extract-name checks are excluded because this synthetic file is deliberately not the real data.
Usage: python source/scale_check.py [columns ...]   Writes report/scale-evidence.json.
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import load
from load import ROOT

ROWS = 75_700  # The respondents in the full GSS cumulative file, from the brief.


def real_records():
    merged = {}
    for path in sorted((ROOT / "source/data/raw").glob("*.json")):
        columns = json.loads(path.read_bytes())["data"]
        for values in zip(*columns.values()):
            record = dict(zip(columns, values))
            merged[(record["year"], record["id_"])] = record
    return list(merged.values())


def add_synthetic_catalog(project, names):
    for seed in ("variables", "codebook"):  # A checkout can hold CRLF, and appending LF rows would mix line endings.
        path = project / f"dbt/seeds/{seed}.csv"
        path.write_text(path.read_text(encoding="utf8"), encoding="utf8", newline="\n")
    with (project / "dbt/seeds/variables.csv").open("a", encoding="utf8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        for name in names:
            writer.writerow([name, "synthetic", "category", "", "", "2014|2016|2018", "synthetic", "false", "false", "false", ""])
    with (project / "dbt/seeds/codebook.csv").open("a", encoding="utf8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        for name in names:
            writer.writerows([[name, 1, "YES", "answer"], [name, 2, "NO", "answer"], [name, -100, ".i:  Inapplicable", "inapplicable"]])


def synthetic_extract(records, names):
    columns = {name: [] for name in records[0]}
    for index in range(ROWS):
        record = records[index % len(records)]
        for name, values in columns.items():
            values.append(record[name])
        columns["id_"][-1] = index + 1
    for name in names:
        columns[name] = (["YES", "NO", ".i:  Inapplicable"] * (ROWS // 3 + 1))[:ROWS]
    return json.dumps({"data": columns, "codes": {}}).encode()


def measure(records, column_count, scratch):
    project = scratch / str(column_count)
    project.mkdir()
    shutil.copytree(ROOT / "dbt", project / "dbt", ignore=shutil.ignore_patterns("target", "logs"))
    extra = [f"synthetic_{i}" for i in range(column_count - 30)]
    add_synthetic_catalog(project, extra)
    raw = project / "synthetic.json"
    raw.write_bytes(synthetic_extract(records, extra))
    result = dict(rows=ROWS, columns=column_count, answer_rows=ROWS * column_count, json_mb=round(raw.stat().st_size / 1e6))
    database = project / "gss.duckdb"
    load.ROOT = project
    start = time.perf_counter()
    try:
        with duckdb.connect(str(database)) as con:
            load.load(con, [raw])
    except duckdb.Error as exc:
        return result | dict(load_s=round(time.perf_counter() - start, 1), failed_at="load", error=str(exc)[:120])
    finally:
        load.ROOT = ROOT
    result["load_s"] = round(time.perf_counter() - start, 1)
    start = time.perf_counter()
    env = dict(os.environ, GSS_DB=str(database), DBT_SEND_ANONYMOUS_USAGE_STATS="false", PYTHONUTF8="1", DBT_USE_COLORS="false")
    dbt = subprocess.run([sys.executable, "-c", "from dbt.cli.main import cli; cli()", "build", "--profiles-dir", ".",
                          "--exclude", "wave_row_counts", "wave_weight_totals", "metadata_contract", "--target-path", str(project / "target")],
                         cwd=project / "dbt", env=env, capture_output=True, text=True, encoding="utf8", errors="replace")
    result["dbt_s"] = round(time.perf_counter() - start, 1)
    if dbt.returncode:
        errors = [line.split("  ", 1)[-1].strip() for line in dbt.stdout.splitlines() if "Error" in line]
        return result | dict(failed_at="dbt", error=" | ".join(errors[:2])[:300])
    return result | dict(database_gb=round(database.stat().st_size / 1e9, 2))


def main():
    shapes = [int(value) for value in sys.argv[1:]] or [30, 100, 300]
    records = real_records()
    results = []
    with TemporaryDirectory(prefix="scale-") as temp:
        for column_count in shapes:
            results.append(measure(records, column_count, Path(temp)))
            print(results[-1], flush=True)
            shutil.rmtree(Path(temp) / str(column_count), ignore_errors=True)
            if "failed_at" in results[-1]:
                break
    (ROOT / "report/scale-evidence.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()

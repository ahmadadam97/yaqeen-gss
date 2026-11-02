"""Run locally from any directory with the project's virtual environment active."""
import csv
import logging
import os
import subprocess
import sys
from tempfile import TemporaryDirectory
from pathlib import Path

import duckdb
from load import ROOT, load
from tv_diagnostics import summarize


def publish_results(con, sql_dir, results):
    with TemporaryDirectory(dir=results.parent) as temp:
        stage = Path(temp)
        for path in sorted(sql_dir.glob("*.sql")):
            query = con.execute(path.read_text(encoding="utf8"))
            with (stage / path.with_suffix(".csv").name).open("w", newline="", encoding="utf8") as f:
                writer = csv.writer(f)
                writer.writerow([col[0] for col in query.description])
                writer.writerows(query.fetchall())
            logging.info("completed %s", path.name)
        diagnostic = summarize(con)
        with (stage / "04_tv_rank_tests.csv").open("w", newline="", encoding="utf8") as f:
            writer = csv.DictWriter(f, fieldnames=list(diagnostic))
            writer.writeheader()
            writer.writerow(diagnostic)
        for obsolete in results.glob("*.csv"):
            if not (stage / obsolete.name).exists():
                obsolete.unlink()
        for output in stage.iterdir():
            output.replace(results / output.name)
        (results / "_SUCCESS").write_text("Complete\n", encoding="utf8")


def main():
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(build / "run.log")])
    database = Path(os.environ.get("GSS_DB", build / "gss.duckdb")).resolve()
    env = dict(os.environ, GSS_DB=str(database), DBT_SEND_ANONYMOUS_USAGE_STATS="false",
               PYTHONUTF8="1", DBT_USE_COLORS="false")
    dbt = Path(sys.executable).with_name("dbt.exe" if os.name == "nt" else "dbt")
    try:
        results = build / "results"
        results.mkdir(exist_ok=True)
        (results / "_SUCCESS").unlink(missing_ok=True)
        paths = sorted((ROOT / "source/data/raw").glob("*.json"))
        required = {"yaqeen_cut_a_2014_2016.json", "yaqeen_cut_b_2016_2018.json"}
        if missing := required - {p.name for p in paths}:
            raise ValueError(f"missing assessment cut(s): {sorted(missing)}")
        logging.info("start load")
        with duckdb.connect(str(database)) as con:
            load(con, paths)
        for args in (["build"], ["docs", "generate"]):
            logging.info("start dbt %s", " ".join(args))
            subprocess.run([str(dbt), *args, "--profiles-dir", "."], cwd=ROOT / "dbt", env=env, check=True)
        with duckdb.connect(str(database), read_only=True) as con:
            publish_results(con, ROOT / "source/sql", results)
        logging.info("run succeeded")
    except Exception:
        logging.exception("run failed; downstream stages stopped")
        raise


if __name__ == "__main__":
    main()

"""Run locally from any directory with the project's virtual environment active."""
import csv
import logging
import os
import subprocess
import sys
from pathlib import Path

import duckdb
from load import ROOT, load


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
        logging.info("start load")
        with duckdb.connect(str(database)) as con:
            load(con, sorted((ROOT / "source/data/raw").glob("*.json")))
        for args in (["build"], ["docs", "generate"]):
            logging.info("start dbt %s", " ".join(args))
            subprocess.run([str(dbt), *args, "--profiles-dir", "."], cwd=ROOT / "dbt", env=env, check=True)
        with duckdb.connect(str(database), read_only=True) as con:
            results = build / "results"
            results.mkdir(exist_ok=True)
            for path in sorted((ROOT / "source/sql").glob("*.sql")):
                query = con.execute(path.read_text(encoding="utf8"))
                with (results / path.with_suffix(".csv").name).open("w", newline="", encoding="utf8") as f:
                    writer = csv.writer(f)
                    writer.writerow([col[0] for col in query.description])
                    writer.writerows(query.fetchall())
                logging.info("completed %s", path.name)
        logging.info("run succeeded")
    except Exception:
        logging.exception("run failed; downstream stages stopped")
        raise


if __name__ == "__main__":
    main()

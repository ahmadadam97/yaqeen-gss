"""Build a candidate snapshot and publish its database and results together."""
import csv
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import duckdb
from load import ROOT, load
from snapshot import build_root, definition_digest, digest
from tv_diagnostics import summarize


def publish_results(con, sql_dir, results):
    """Write only into an unpublished candidate run."""
    results.mkdir(parents=True, exist_ok=True)
    paths = sorted(sql_dir.glob("*.sql"))
    if not paths:
        raise ValueError(f"no compiled analyses in {sql_dir}")
    for path in paths:
        query = con.execute(path.read_text(encoding="utf8"))
        with (results / path.with_suffix(".csv").name).open("w", newline="", encoding="utf8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow([col[0] for col in query.description])
            writer.writerows(query.fetchall())
        logging.info("completed %s", path.name)
    diagnostic = summarize(con)
    with (results / "04_tv_rank_tests.csv").open("w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=list(diagnostic), lineterminator="\n")
        writer.writeheader()
        writer.writerow(diagnostic)


def definition_paths(root):
    """Everything that decides a result. Filter on paths inside the repository, wherever it is checked out."""
    paths = [root / "docs/extracts.csv", root / "requirements.lock",
             *sorted((root / "dbt").rglob("*.sql")), *sorted((root / "dbt").rglob("*.yml")),
             *sorted((root / "dbt/seeds").glob("*.csv")), *sorted((root / "source").rglob("*.py"))]
    generated = {"target", "logs"}
    return [p for p in paths if not generated & set(p.relative_to(root).parts)]


def log_dbt_failures(target):
    """Name each failed model or test in run.log, not only in dbt's own log."""
    results = target / "run_results.json"
    if results.exists():
        for result in json.loads(results.read_text(encoding="utf8"))["results"]:
            if result["status"] in ("error", "fail"):
                logging.error("dbt %s %s: %s", result["status"], result["unique_id"], result["message"])


def publish_run(candidate, build, manifest):
    run_id = manifest["run_id"]
    (candidate / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf8")
    destination = build / "runs" / run_id
    candidate.replace(destination)
    pointer = build / ("LATEST." + run_id + ".tmp")
    try:
        pointer.write_text(run_id + "\n", encoding="utf8")
        pointer.replace(build / "LATEST")
    finally:
        pointer.unlink(missing_ok=True)


def main():
    if os.environ.get("GSS_DB"):
        raise ValueError("Use GSS_BUILD to select the build directory; the runner selects its candidate GSS_DB")
    build = build_root()
    (build / "runs").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(build / "run.log")])
    lock = build / ".run.lock"
    try:
        lock.mkdir()  # One writer also protects dbt's shared project artifacts.
    except FileExistsError:
        logging.error("another run holds %s; if no run is active, remove that folder and rerun", lock)
        raise
    try:
        with TemporaryDirectory(prefix=".candidate-", dir=build / "runs") as temp:
            candidate = Path(temp)
            database = candidate / "gss.duckdb"
            run_id = uuid4().hex
            paths = sorted((ROOT / "source/data/raw").glob("*.json"))
            logging.info("start candidate run=%s", run_id)
            with duckdb.connect(str(database)) as con:
                load(con, paths, ROOT / "docs/extracts.csv")
            env = dict(os.environ, GSS_DB=str(database), DBT_SEND_ANONYMOUS_USAGE_STATS="false",
                       PYTHONUTF8="1", DBT_USE_COLORS="false")
            dbt = [sys.executable, "-c", "from dbt.cli.main import cli; cli()"]
            invocation = None
            for args in (["build"], ["docs", "generate"]):
                logging.info("start dbt %s run=%s", " ".join(args), run_id)
                try:
                    subprocess.run([*dbt, *args, "--profiles-dir", ".", "--target-path", str(candidate / "dbt")],
                                   cwd=ROOT / "dbt", env=env, check=True)
                except subprocess.CalledProcessError:
                    log_dbt_failures(candidate / "dbt")
                    raise
                if args == ["build"]:
                    invocation = json.loads((candidate / "dbt/run_results.json").read_text(encoding="utf8"))["metadata"]["invocation_id"]
            with duckdb.connect(str(database), read_only=True) as con:
                publish_results(con, candidate / "dbt/compiled/gss/analyses", candidate / "results")
                relations = {"raw.records": "raw.records", "stg_membership": "staging.stg_membership",
                             "answers": "marts.answers", "respondents": "marts.respondents"}
                counts = {name: con.execute(f"select count(*) from {relation}").fetchone()[0]
                          for name, relation in relations.items()}
                inputs = [dict(filename=name, sha256=sha, row_count=n)
                          for name, sha, n in con.execute("select * from raw.files order by filename").fetchall()]
            outputs = {path.relative_to(candidate).as_posix(): digest(path)
                       for path in [database, *sorted((candidate / "results").glob("*.csv"))]}
            manifest = dict(run_id=run_id, dbt_invocation_id=invocation, inputs=inputs, row_counts=counts, outputs=outputs,
                            definitions={p.relative_to(ROOT).as_posix(): definition_digest(p) for p in definition_paths(ROOT)})
            publish_run(candidate, build, manifest)
            logging.info("published run=%s counts=%s", run_id, counts)
    except Exception:
        logging.exception("candidate failed; LATEST and the previous published run remain available")
        raise
    finally:
        lock.rmdir()


if __name__ == "__main__":
    main()

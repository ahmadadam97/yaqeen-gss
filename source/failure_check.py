"""Corrupt a copy of the project in known ways and record which check stops each one.

Takes about a minute and is not part of a normal run. Usage: python source/failure_check.py
Writes report/failure-evidence.csv. Exits nonzero if a case behaves differently from what it expects.
"""
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

from load import ROOT

CUT_A, CUT_B = "yaqeen_cut_a_2014_2016.json", "yaqeen_cut_b_2016_2018.json"


def read(project, name):
    return json.loads((project / "source/data/raw" / name).read_bytes())


def write(project, name, doc):
    (project / "source/data/raw" / name).write_text(json.dumps(doc), encoding="utf8")


def review_manifest(project):
    """Do what a reviewer would do after accepting a new file, so later checks are the ones under test."""
    path = project / "docs/extracts.csv"
    with path.open(encoding="utf8", newline="") as f:
        entries = list(csv.DictReader(f))
    for entry in entries:
        content = (project / "source/data/raw" / entry["filename"]).read_bytes()
        entry["sha256"] = hashlib.sha256(content).hexdigest()
        try:
            years = json.loads(content)["data"]["year"]
        except ValueError:
            continue
        entry["row_count"], entry["years"] = len(years), "|".join(sorted({str(y) for y in years}))
    with path.open("w", encoding="utf8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(entries[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(entries)


def rows_where(doc, year=None, **equals):
    data = doc["data"]
    return [i for i in range(len(data["year"]))
            if (year is None or str(data["year"][i]) == str(year)) and all(data[k][i] == v for k, v in equals.items())]


def edit(name, change):
    """Apply change(doc) to one extract, then review the manifest."""
    def apply(project):
        doc = read(project, name)
        change(doc)
        write(project, name, doc)
        review_manifest(project)
    return apply


def set_first(column, value, year=2014, **equals):
    def change(doc):
        doc["data"][column][rows_where(doc, year, **equals)[0]] = value
    return change


def truncate(project):
    path = project / "source/data/raw" / CUT_A
    path.write_bytes(path.read_bytes()[:1000])
    review_manifest(project)


def edit_without_review(project):
    doc = read(project, CUT_A)
    doc["data"]["tvhours"][rows_where(doc, 2014, ballot="Ballot a")[0]] = "7"
    write(project, CUT_A, doc)


def duplicate_key(doc):
    doc["data"]["id_"][1] = doc["data"]["id_"][0]


def overlap_conflict(doc):
    index = rows_where(doc, 2016)[0]
    doc["data"]["age"][index] = "18" if doc["data"]["age"][index] != "18" else "19"


def unknown_column(doc):
    doc["data"]["new_item"] = ["x"] * len(doc["data"]["year"])


def drop_half_of_2018(doc):
    keep = [i for i, year in enumerate(doc["data"]["year"]) if str(year) != "2018" or i % 2]
    doc["data"] = {name: [values[i] for i in keep] for name, values in doc["data"].items()}


def blank_postlife_2018(doc):
    for index in rows_where(doc, 2018):
        doc["data"]["postlife"][index] = None


def drop_pray(doc):
    del doc["data"]["pray"]


def web_time_for_nonuser(doc):
    index = rows_where(doc, 2014, ballot="Ballot a")[0]
    doc["data"]["usewww"][index], doc["data"]["wwwhr"][index], doc["data"]["wwwmin"][index] = "NO", "40", "0"


def rotate_pray_2018(doc):
    indexes = rows_where(doc, 2018)
    values = [doc["data"]["pray"][i] for i in indexes]
    for index, value in zip(indexes, values[1:] + values[:1]):
        doc["data"]["pray"][index] = value


def rename_cut(project):
    (project / "source/data/raw" / CUT_A).rename(project / "source/data/raw/renamed.json")
    path = project / "docs/extracts.csv"
    path.write_text(path.read_text(encoding="utf8").replace(CUT_A, "renamed.json"), encoding="utf8")


# (what goes wrong, what corrupts it, the check expected to stop it). None means nothing can stop it from this data.
CASES = [
    ("Truncated file", truncate, "loader"),
    ("File edited without review", edit_without_review, "loader"),
    ("Duplicate interview in a file", edit(CUT_A, duplicate_key), "loader"),
    ("Overlap answers disagree between cuts", edit(CUT_B, overlap_conflict), "loader"),
    ("Column with no catalog entry", edit(CUT_A, unknown_column), "loader"),
    ("Label not in the codebook", edit(CUT_A, set_first("pray", "Sometimes")), "invalid_answers"),
    ("TV hours out of range (99)", edit(CUT_A, set_first("tvhours", "99", ballot="Ballot a")), "invalid_answers"),
    ("A wave outside the reviewed years", edit(CUT_A, set_first("year", "2022")), "invalid_answers"),
    ("Half of 2018 deleted, manifest resealed", edit(CUT_B, drop_half_of_2018), "wave_row_counts"),
    ("One 2018 weight set to 5000", edit(CUT_B, set_first("wtssps", "5000", year=2018)), "wave_weight_totals"),
    ("POSTLIFE blank for all of 2018", edit(CUT_B, blank_postlife_2018), "wave_coverage"),
    ("PRAY column missing from cut B", edit(CUT_B, drop_pray), "wave_coverage"),
    ("EVWORK answered by a full-time worker", edit(CUT_A, set_first("evwork", "YES", wrkstat="Working full time")), "survey_routing"),
    ("NEWS answered on ballot C", edit(CUT_A, set_first("news", "Never", ballot="Ballot c")), "survey_routing"),
    ("SATJOB answered by a retiree", edit(CUT_A, set_first("satjob", "Very satisfied", wrkstat="Retired")), "survey_routing"),
    ("Web hours from someone who said no web", edit(CUT_A, web_time_for_nonuser), "survey_routing"),
    ("A ballot the rules do not cover", edit(CUT_A, set_first("ballot", "Ballot d")), "survey_routing"),
    ("Cut renamed but seed not updated", rename_cut, "metadata_contract"),
    ("Column shifted one row within a wave", edit(CUT_B, rotate_pray_2018), None),
]


def run_case(case, scratch):
    index, (problem, corrupt, expected) = case
    project = scratch / str(index)
    shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns(".env", ".venv", ".git", "build", "target", "logs", "__pycache__"))
    corrupt(project)
    build = project / "build"
    (build / "runs/prior").mkdir(parents=True)
    (build / "LATEST").write_text("prior\n")
    env = {k: v for k, v in os.environ.items() if k != "GSS_DB"}
    done = subprocess.run([sys.executable, "source/run.py"], cwd=project, env=dict(env, PYTHONUTF8="1", GSS_BUILD=str(build)),
                          capture_output=True, text=True, encoding="utf8", errors="replace")
    log = (build / "run.log").read_text(encoding="utf8", errors="replace")
    failed = re.findall(r"dbt (?:fail|error) \w+\.gss\.(\w+)", log)
    # A bad value can fail more than one test; report the check this case exists to exercise when it fired.
    if done.returncode == 0:
        stopped_by = None
    elif expected in failed:
        stopped_by = expected
    else:
        stopped_by = failed[0] if failed else "loader"
    kept = (build / "LATEST").read_text().strip() == "prior"
    return dict(problem=problem, expected=expected or "not detectable", stopped_by=stopped_by or "not detected",
                previous_run_kept=str(kept).lower(), as_expected=str(stopped_by == expected and kept == (expected is not None)).lower())


def main():
    with TemporaryDirectory(prefix="failure-check-") as temp:
        with ThreadPoolExecutor(4) as pool:
            results = list(pool.map(lambda case: run_case(case, Path(temp)), enumerate(CASES)))
    with (ROOT / "report/failure-evidence.csv").open("w", encoding="utf8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)
    for result in results:
        print(f"{result['as_expected']:5} {result['problem']:42} expected={result['expected']:18} stopped_by={result['stopped_by']}")
    if any(result["as_expected"] != "true" for result in results):
        sys.exit("A case behaved differently from what it expects")


if __name__ == "__main__":
    main()

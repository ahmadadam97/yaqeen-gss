# GSS interviews | 2014, 2016 and 2018

A local Python, DuckDB and dbt pipeline for two overlapping NORC survey extracts. It counts 7,753 interviews using (survey year, respondent ID). Each successful run publishes one database, its results, dbt documentation and a provenance manifest together.

**Start with the [report](report/survey-assessment.pdf).** It has the answers, the decisions behind them and what remains open.

## Run it

Use Python 3.12 on Windows (tested with 3.12.10 on Windows 11). No cloud resources or credentials are needed.

```powershell
py -3.12 -m venv .env
.env\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements.lock
.env\Scripts\python.exe source/run.py
```

`requirements.lock` pins every pipeline package by hash, so a run next month behaves like a run today. The database and results appear under `build/runs/<run ID>`, and `build/LATEST` names the current run.

## Run the tests

```powershell
.env\Scripts\python.exe -m unittest discover -s source -p "test_*.py" -v
```

`source/run.py` also runs every dbt test, and a failing test stops the run. Three slower checks produce the evidence in the report:

```powershell
.env\Scripts\python.exe source/failure_check.py
.env\Scripts\python.exe source/scale_check.py
.env\Scripts\python.exe source/benchmark.py
```

`failure_check.py` corrupts copies of the project and records which check stops each one. `scale_check.py` measures the load and dbt build at larger shapes. `benchmark.py` compares each query against a view and a table.

## Rebuild the report

The renderer needs one extra package, which the pipeline itself does not. Install it in the same environment:

```powershell
.env\Scripts\python.exe -m pip install reportlab==4.4.9
.env\Scripts\python.exe report/build_report.py
```

All statistics come from the published CSVs and the evidence files in `report/`. Run `benchmark.py` first if a model or query has changed, because the renderer refuses benchmark evidence from different definitions. It also refuses a report body over five pages.

## Query the data

```python
import sys
sys.path.insert(0, "source")
from snapshot import current_run
folder, manifest = current_run()
print(folder / "gss.duckdb")
```

Open that database read-only. Analysts use `marts.respondents` (one row per interview) and `marts.answers` (one row per interview and variable, with the reason for any missing answer). To browse the dbt documentation, run this from the `dbt` folder, with the run ID from `build/LATEST`:

```powershell
..\.env\Scripts\dbt.exe docs serve --profiles-dir . --target-path ..\build\runs\<run ID>\dbt
```

## How a run works

1. **Validate and load.** `source/load.py` checks each file against the reviewed manifest `docs/extracts.csv` (hash, row count and years), then checks JSON structure, keys, the codebook and overlap agreement. Raw rows go to `raw.records` unchanged.
2. **Build and test.** dbt builds seeds and models, and runs tests including per-wave row counts, coverage floors and survey routing.
3. **Document and analyze.** dbt generates docs and compiles the analyses, and the runner executes them.
4. **Publish.** The new run is renamed into place and only then does a small pointer file, `build/LATEST`, switch to it.

**When something fails:** the run stops, `build/run.log` names the stage and any failed test, `dbt/logs/dbt.log` has the detail, and the previous run stays published. Fix the cause and run the same command again; every run starts from an empty database, so rerunning is always safe.

**What triggers a run:** a person, after reviewing a new extract or definition. A CI workflow also runs on each push and pull request (`.github/workflows/check.yml`). A failing CI run marks the commit and pull request as failed. It does not block a merge, because the repository has no required checks; making `survey-checks` a required check on `main` would add that block.

**A new extract:** add the file and its reviewed hash to `docs/extracts.csv`, name its cut in `dbt/seeds/extract_cuts.csv` if it is part of the audit, and for a new wave add its year to `variables.csv`, its rows to `eligibility.csv` and its count to `wave_expectations.csv`. Everything then rebuilds. A hash update is a review decision; recomputing it blindly defeats the check.

**Interrupted runs:** a `.run.lock` folder allows one run at a time. After a crash, confirm nothing is running, then remove `build/.run.lock`. A leftover `build/runs/.candidate-*` folder is safe to delete.

**Configuration:** the only setting is the optional `GSS_BUILD` environment variable, which selects another build folder. Nothing environment-specific is committed. The runner rejects a `GSS_DB` setting because it selects its own database.

## Repository map

| Path | Contents |
|---|---|
| `source/data/raw/` | The two committed extracts, byte for byte |
| `source/load.py`, `run.py`, `snapshot.py`, `tv_diagnostics.py` | Validation and load, orchestration, reading a published run, Q4 rank tests |
| `source/test_*.py` | Unit tests |
| `source/failure_check.py`, `scale_check.py`, `benchmark.py` | Evidence for the report |
| `dbt/models/staging`, `dbt/models/marts` | The transformation layers |
| `dbt/seeds/` | Semantic metadata: codebook, variables, eligibility, work status, wave counts, cuts |
| `dbt/tests/` | Data expectations |
| `dbt/analyses/` | The six required queries, overlap audit, coverage and sensitivities |
| `docs/design.md` | Design note, and where the build diverged from it |
| `docs/naming.md` | Naming convention |
| `docs/profile.md`, `profile.csv` | Pre-build data profile |
| `docs/extracts.csv` | Reviewed source manifest |
| `docs/analyst-guide.md` | Analytical definitions and the weight decision |
| `docs/production.md` | AWS sketch and additional sources |
| `report/survey-assessment.pdf` | The report |
| `report/results/` | Committed analytical output and a guide to reading it |
| `.github/workflows/check.yml` | CI: clean install, tests, pipeline, comparison with committed results |

## Reproduce the extracts

In the [GSS Data Explorer](https://gssdataexplorer.norc.org), build two independent cuts, A (2014 and 2016) and B (2016 and 2018), with no case or complete-case filters, using these variables:

```
year id_ ballot form mode age sex region
wrkstat evwork educ degree indus10 satjob
postlife pray relig16 relig attend reliten
news tvhours inttech wwwhr wwwmin compuse webmob emailhr emailmin usewww
wtssps wtssnrps
```

Select JSON and the metadata workbook (Label), then download from MyGSS, Extracts. Open `batch_0.zip` and keep `result/post_processing_output.json` byte for byte under the cut's name in `source/data/raw/`. The companion `GSS.json` uses Python literal notation and is not valid JSON. Future NORC releases can produce different bytes and would need a newly reviewed manifest.

The cuts contain 5,405 and 5,215 records and share 2,867 interviews, so their union has 7,753.

## Source

Davern, Michael; Bautista, Rene; Freese, Jeremy; Herd, Pamela; and Morgan, Stephen L;, General Social Surveys, 1972–2024 [machine-readable data file] /Principal Investigator, Smith, Tom W.; Co-Principal Investigators, Rene Bautista, Jeremy Freese, Pamela Herd, and Stephen L. Morgan; Sponsored by National Science Foundation. --NORC ed.-- Chicago: NORC, 2025: NORC at the University of Chicago [producer and distributor]. Data accessed from the GSS Data Explorer at [gssdataexplorer.norc.org](https://gssdataexplorer.norc.org/). Citation follows the [Data Explorer terms](https://gssdataexplorer.norc.org/terms_and_conditions). The [NORC questionnaires](https://gss.norc.org/get-documentation/questionnaires.html) document wording and routing.

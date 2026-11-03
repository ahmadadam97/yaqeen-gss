# GSS interviews | 2014, 2016 and 2018

A local Python, DuckDB and dbt pipeline for two independently selected NORC survey extracts. It counts 7,753 interviews using (survey year, respondent ID). Each successful publication contains one database, its complete results, dbt documentation and a provenance manifest.

## Run from the repository root

Use Python 3.12 (tested with 3.12.10). Windows PowerShell:

```powershell
py -3.12 -m venv .env
.env\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements.lock
.env\Scripts\python.exe -m pip check
.env\Scripts\python.exe -m unittest discover -s source -p "test_*.py" -v
.env\Scripts\python.exe source/run.py
```

On macOS or Linux, use `python3.12 -m venv .env` and substitute `.env/bin/python`. The pinned requirements.lock contains wheel hashes verified against PyPI release metadata. requirements.txt lists the same versions in readable form. No cloud resources or credentials are required.

## One complete publication

Every attempt builds a fresh `build/runs/.candidate-.../gss.duckdb` from reviewed input files. It validates their manifest, builds and tests dbt, generates documentation, then executes all SQL and the TV diagnostic. All tables rebuild at this scale. After closing the database, it hashes the database and every result and writes a manifest with the run ID, input hashes/counts, definition hashes, row counts and dbt build invocation ID. It renames the completed candidate directory and atomically replaces the small `build/LATEST` pointer on the same filesystem.

Readers resolve LATEST once and verify the output hashes. A failure before pointer replacement leaves the prior successful publication available. Per-file replacement cannot expose a mixed published result set. The local filesystem must support atomic rename. A .run.lock directory enforces one writer; after an interrupted process, confirm it has stopped before removing that lock. Unreferenced complete runs can remain after a pointer-write failure. Retain or remove old runs deliberately.

**Configuration and migration.** `GSS_BUILD` optionally selects another build directory. The old `GSS_DB` runner override is replaced by GSS_BUILD because database and CSV selection must be coupled. Unset a legacy GSS_DB before invoking the runner or renderer. The runner supplies candidate GSS_DB only to dbt. Old build/gss.duckdb and build/results from earlier versions are legacy artifacts; LATEST is authoritative.

To inspect the current run from the project environment:

```python
import sys
sys.path.insert(0, "source")
from snapshot import current_run
folder, manifest = current_run()
print(folder / "gss.duckdb")
print(manifest["row_counts"])
```

Use that database read-only for analysis. To serve its dbt documentation, select that run's dbt target directory in the dbt docs serve command. No credentials are stored. build/run.log and dbt/logs/dbt.log record stages, hashes, counts and exceptions. The trigger is a manual run after a reviewed extract or definition changes.

## Recovery and reviewed source data

docs/extracts.csv records the two exact JSON filenames, hashes, row counts, years and export settings. The loader asserts file membership, byte hashes, counts and years before accepting the candidate. This detects a truncated first input as well as later changes. Column lengths, keys, codebook drift and overlap conflicts are also checked. A field intentionally absent in an extract retains absent_field.

For a malformed or semantically invalid new snapshot, the candidate fails and is discarded. Correct the source or metadata, review/update its manifest entry where source bytes intentionally changed, then run the same command. The previous published run remains available until success. A hash update is an explicit review decision; blindly recomputing hashes would defeat this check. A manifest cannot prove that an upstream export's equally long columns were correctly aligned.

The low-level load() function still supports transactional incremental inserts for its isolated tests. The production runner intentionally uses an empty candidate each time. Rerun safety now comes from complete reconstruction and atomic publication, so it does not depend on an insert-skip shortcut.

## Where to look

| Path | Contents |
|---|---|
| docs/profile.md and profile.csv | Original pre-build profile for all 96 variable/year combinations |
| docs/extracts.csv | Reviewed source manifest |
| docs/design.md and naming.md | Initial design, current divergence and conventions |
| docs/review-response.md | Accepted/rejected feedback, source definitions, evidence and limitations |
| source/load.py, run.py and snapshot.py | Ingestion, candidate orchestration and verified reader |
| dbt/seeds | Codebook, variable domains/projections, ballot/form eligibility and work-status definitions |
| dbt/models and tests | Membership, canonical answers, wide respondents and data expectations |
| source/sql | Six required analyses, overlap audit, coverage/research extensions and report/sensitivity outputs |
| report/results | Committed analytical output and interpretation guide |
| report/survey-assessment.pdf | Five-page interactive report |
| build/runs/<run ID> | Generated database, CSVs, manifest and dbt artifacts |
| .github/workflows/check.yml | Clean installation, Python tests, dbt build/docs and result comparison |

## Metadata and missing values

variables.csv chooses label/value/status projections in the wide table. Jinja reads those flags after the seed dependency is built. A new item can enter the canonical answer model through its catalog and codebook entries. Set projection flags if analysts also need it in the wide table.

eligibility.csv expresses the reviewed year/ballot/form availability for split items. A source .i outside that item's eligible combinations becomes not_asked_ballot. The original codebook meaning is preserved separately in source_status. Other .i answers remain inapplicable. Unknown ballot/form combinations retain unknown eligibility. An observed answer that violates a reviewed eligibility rule fails a test. work_status.csv marks codes 1-3 as employed and codes 5-8 as eligible for EVWORK.

## Report and performance

After the pipeline succeeds, install optional `reportlab==4.4.9` and `pypdf==6.10.0`, then run `python report/build_report.py` in that environment. The renderer verifies the selected publication and reads all statistics from its CSVs. It has no database-query path. Tabs link pages and the Research page switches survey weights in supporting viewers.

Run `python source/benchmark.py` to compare the current run's compiled-view baselines with its tables. It verifies equal rows for every query and writes plans for the slowest one to report/query-plans.txt. Durations include fetching and exclude the materialization/build cost. Machine timings vary.

## Bonuses and CI

The question/weight guide is in docs/analyst-guide.md. docs/production.md sketches AWS storage, execution, scheduling, permissions, costs and additional sources. These are proposed operations.

The workflow runs on pushes and pull requests. A failed dbt build stops docs and results. The final CI step verifies the publication and compares every committed CSV. Configure branch protection to require the survey-checks job if a failure should block merging.

## Reproduce the extracts

In [GSS Data Explorer](https://gssdataexplorer.norc.org), build independent cuts A (2014/2016) and B (2016/2018), with no case or complete-case filters. Select JSON and the metadata workbook (Label). Download from MyGSS → Extracts. Open batch_0.zip and retain result/post_processing_output.json byte-for-byte under the cut name in source/data/raw. The companion GSS.json uses Python literal notation. Future NORC releases can produce different bytes and require a newly reviewed snapshot.

```
year id_ ballot form mode age sex region
wrkstat evwork educ degree indus10 satjob
postlife pray relig16 relig attend reliten
news tvhours inttech wwwhr wwwmin compuse webmob emailhr emailmin usewww
wtssps wtssnrps
```

The cuts contain 5,405 and 5,215 records, sharing 2,867 interviews. Their union has 7,753. The initial profile and design preceded the implementation in Git history.

## Source

Davern, Michael; Bautista, Rene; Freese, Jeremy; Herd, Pamela; and Morgan, Stephen L;, General Social Surveys, 1972–2024 [machine-readable data file] /Principal Investigator, Smith, Tom W.; Co-Principal Investigators, Rene Bautista, Jeremy Freese, Pamela Herd, and Stephen L. Morgan; Sponsored by National Science Foundation. --NORC ed.-- Chicago: NORC, 2025: NORC at the University of Chicago [producer and distributor]. Data accessed from the GSS Data Explorer at [gssdataexplorer.norc.org](https://gssdataexplorer.norc.org/). Citation follows the [Data Explorer terms](https://gssdataexplorer.norc.org/terms_and_conditions). The [NORC questionnaires](https://gss.norc.org/get-documentation/questionnaires.html) document wording and routing.

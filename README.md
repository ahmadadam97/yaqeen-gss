# GSS survey interviews | 2014, 2016 and 2018

A local Python, DuckDB and dbt project for analysing employment, religiosity and media use across three US General Social Survey waves. The respondent table contains 7,753 interviews. The shared 2016 wave is retained in source membership and counted once in the six substantive queries.

## Run from the repository root

Use Python 3.12 (tested with 3.12.10). Install from the pinned dependency file into a fresh virtual environment. Windows PowerShell:

```powershell
py -3.12 -m venv .env
.env\Scripts\python.exe -m pip install -r requirements.txt
.env\Scripts\python.exe source/run.py
.env\Scripts\python.exe -m unittest discover -s source -p "test_*.py" -v
```

On macOS or Linux use `python3.12 -m venv .env` and substitute `.env/bin/python` for the interpreter above. The core run requires no credentials or cloud services. An optional GSS_DB environment variable selects the database file. Its parent directory must exist.

The runner hashes and loads new raw files together in a transaction, invokes dbt build (seeds, models and tests), generates documentation, then runs the eleven SQL files and the Q4 rank checks. A failed stage exits nonzero and stops the remaining stages. Inspect build/run.log and dbt/logs/dbt.log. Results are staged until every query and diagnostic succeeds. build/results is reserved for generated files; a successful publish removes CSVs from retired queries. Use the CSVs only when build/results/_SUCCESS is present. It is cleared before every run and written after publication. Correct the source or metadata and rerun the same command. Both named cuts and all previously loaded files must remain in place. A renamed file or identical bytes under two filenames is rejected. For intentional source revisions, preserve old inputs separately and use a fresh database for the new, documented snapshot. There is no scheduler to operate. The trigger is a manual run after files or definitions change.

## Where to look

| Path | Contents |
|---|---|
| source/data/raw | Two original strict JSON exports |
| docs/profile.md and profile.csv | Pre-build profile, including all 96 variable/year combinations |
| docs/design.md and naming.md | Grain, database, transformations, assumptions and naming |
| source/load.py and run.py | Ingestion, validations and stage ordering |
| dbt/seeds and dbt/models | Code meanings, reviewed waves, numeric domains, interviews and answers |
| source/sql | Six analyses, the membership audit, two coverage/technology supplements and two research extensions |
| source/tv_diagnostics.py | SciPy rank tests on the Q4 working sample |
| report | Short report, [result interpretation guide](report/results/README.md), complete results and measured query plans |
| build | Generated DuckDB file, execution log and new result CSVs |
| dbt/target | Generated documentation, compiled SQL and test results |

Run dbt commands directly from dbt/ using the environment's dbt executable with `--profiles-dir .`. Use `dbt docs serve --profiles-dir .` after the runner succeeds to browse the model documentation.

Run `python source/benchmark.py` with the same environment after the pipeline to reproduce the query comparison. It times all eleven SQL queries, checks equal results for the slowest query and writes both physical plans to report/query-plans.txt. Timings depend on the machine.

## Bonuses and handoff

- [Question map, weights and panel practice](docs/analyst-guide.md): why the two research extensions follow from the brief, weighting rules and limits.
- [Production sketch](docs/production.md): full-scale AWS storage, compute, schedule, permissions and costs; source contracts for Pew and a possible Yaqeen pilot. Design only.
- [GitHub Actions](.github/workflows/check.yml): pushes and pull requests run Python tests and the complete pipeline, including dbt tests. A failing dbt build exits nonzero before documentation and CSV publication. Once hosted, require the `survey-checks` check in branch protection to block merging. No hosted run or protection rule is claimed.

## Reproduce the inputs

Two consecutive runs against the same initially empty database were checked on 2 November 2026. The first loaded 10,620 raw rows from two files. The second revalidated both files against the current codebook and skipped both inserts. Both runs produced 232,590 decoded answers and 7,753 interviews. SHA-256 digests of the ordered contents of all four relations (raw files, raw records, answers and respondents) matched, and all twelve result CSVs were byte-identical. All five dbt data tests passed on both runs. The original seven analyses also retained every previously reported number after the extra columns and diagnostics were added. The loader's unit tests independently exercise reversed load order and rollback.

### Explorer recipe

In [GSS Data Explorer](https://gssdataexplorer.norc.org), create two independent extracts. Select all variables below, apply no case or complete-case filters, and select JSON plus the metadata workbook (Label). Select 2014 and 2016 for A, then 2016 and 2018 for B. Download both from MyGSS → Extracts → Actions → Download. Inside each archive open batch_0.zip and take result/post_processing_output.json unchanged. Use the cut name as its filename in source/data/raw. The companion GSS.json has equivalent records in Python literal notation. Exact exports can change when NORC publishes a new release.

```
year id_ ballot form mode age sex region
wrkstat evwork educ degree indus10 satjob
postlife pray relig16 relig attend reliten
news tvhours inttech wwwhr wwwmin compuse webmob emailhr emailmin usewww
wtssps wtssnrps
```

A SHA-256: cde0398f3882f45028b93523e98d66f969cdef21f727f97b4ca9b509a6f5976f  
B SHA-256: 46ef44eb95319098e7990e41cf470738fd0f8c22193e1aabde2bf97ae9fe6e7b

Codebook seed values come from the CodeLabel dictionaries in both supplied files. The decoded model joins the exported text to each variable's labels. A number with a unit label uses its mapped code, including zero hours. Unlabelled numeric measurements use documented domain checks. Two industry codes share the label “Uncodeable”; neither is assigned a numeric industry. The full raw code mapping is retained.

## Source

Davern, Michael; Bautista, Rene; Freese, Jeremy; Herd, Pamela; and Morgan, Stephen L;, General Social Surveys, 1972–2024 [machine-readable data file] /Principal Investigator, Smith, Tom W.; Co-Principal Investigators, Rene Bautista, Jeremy Freese, Pamela Herd, and Stephen L. Morgan; Sponsored by National Science Foundation. --NORC ed.-- Chicago: NORC, 2025: NORC at the University of Chicago [producer and distributor]. Data accessed from the GSS Data Explorer website at [gssdataexplorer.norc.org](https://gssdataexplorer.norc.org/). Citation follows the [Data Explorer terms](https://gssdataexplorer.norc.org/terms_and_conditions). The [NORC questionnaires](https://gss.norc.org/get-documentation/questionnaires.html) document survey wording and routing.

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

The runner hashes and loads new raw files together in a transaction, invokes dbt build (seeds, models and tests), generates documentation, then runs the seven SQL files. A failed stage exits nonzero and stops the remaining stages. Inspect build/run.log and dbt/logs/dbt.log. Existing result files reflect the last run that wrote them. Check the most recent run status before using them. Correct the source or metadata and rerun the same command. If replacing a previously loaded file with a corrected version, retain the old raw version and rebuild into a fresh database path. There is no scheduler to operate. The trigger is a manual run after files or definitions change.

## Where to look

| Path | Contents |
|---|---|
| source/data/raw | Two original strict JSON exports |
| docs/profile.md and profile.csv | Pre-build profile, including all 96 variable/year combinations |
| docs/design.md and naming.md | Grain, database, transformations, assumptions and naming |
| source/load.py and run.py | Ingestion, validations and stage ordering |
| dbt/seeds and dbt/models | Code meanings, reviewed waves, numeric domains, interviews and answers |
| source/sql | Six analyses and the cut membership audit |
| report | Short report, complete query results and measured query plans |
| build | Generated DuckDB file, execution log and new result CSVs |
| dbt/target | Generated documentation, compiled SQL and test results |

Run dbt commands directly from dbt/ using the environment's dbt executable with `--profiles-dir .`. Use `dbt docs serve --profiles-dir .` after the runner succeeds to browse the model documentation.

Run `python source/benchmark.py` with the same environment after the pipeline to reproduce the query comparison. It times all seven queries, checks equal results for the slowest query and writes both physical plans to report/query-plans.txt. Timings depend on the machine.

## Reproduce the inputs

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

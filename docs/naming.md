# Naming conventions

Everything in the dbt layer uses lower snake case. Names say what a thing is to an analyst, not how it was built.

| Item | Convention | Example |
|---|---|---|
| Schemas | The layer they hold | `raw`, `staging`, `marts`, `metadata` |
| Folders | Match the schema | `dbt/models/staging`, `dbt/models/marts` |
| Staging models | `stg_` plus what they expose | `stg_membership`, `stg_answers` |
| Mart models | Plural noun for what one row is | `respondents`, `answers` |
| Sources | The schema name, and the table the loader wrote | `raw.records`, `raw.files` |
| Seeds | Plural noun for what they list, or the name of the reference they hold | `variables`, `extract_cuts`, `codebook`, `eligibility` |
| Singular tests | The expectation they enforce | `wave_coverage`, `survey_routing` |
| Analyses | Number plus topic, so results list in question order | `06_wave_changes` |
| Result files | The same name as their analysis, or a `04_` name for the rank tests computed in Python | `report/results/06_wave_changes.csv` |
| Variables | NORC's name, so the codebook stays searchable | `wrkstat`, `relig16` |

The only renamed source fields are `year` and `id_`, exposed as `survey_year` and `respondent_id`.

## Column suffixes and prefixes

| Pattern | Meaning | Example |
|---|---|---|
| no suffix | Readable label for a genuine answer | `pray` |
| `_value` | The numeric value or code | `pray_value`, `tvhours_value` |
| `_status` | Why an answer is or is not available | `postlife_status` |
| `_n` | A raw count of respondents | `valid_n` |
| `_pct` | A percentage | `yes_pct` |
| `_pp` | A percentage-point difference | `news_change_pp` |
| `wtssps_` | Estimated with the WTSSPS weight; without it, a column is unweighted | `wtssps_yes_pct` |
| `is_` | A true or false fact | `is_working`, `is_small_group` |
| `_eligible` | A true or false routing rule, read as "eligible for" | `satjob_eligible` |

## SQL style

Keywords are lower case. One selected column per line where a query has more than a few. Each common table expression has a descriptive name, and joined tables use full-word aliases. Every analysis starts with a comment saying what it answers. Models and analyses refer to relations through `ref()` and `source()`, never by a literal schema name.

## Adding a variable

1. Select it in the Explorer, add it to the extract, and record the reviewed hash and row count in `docs/extracts.csv`.
2. Append a row to `dbt/seeds/variables.csv`: its kind, range, reviewed years, wide-table flags and `min_valid_pct`.
3. Append its exported labels to `dbt/seeds/codebook.csv`.
4. If it appears only on some ballots or forms, add its rows to `dbt/seeds/eligibility.csv`.

The loader, overlap check, `answers` and `respondents` then handle it with no model change. A new wave also needs a questionnaire and routing review before its year is added.

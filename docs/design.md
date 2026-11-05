# Design before implementation
Count interviews using (survey year, respondent ID). The waves are repeated cross sections. A raw file and its row number identify a source observation. Each file retains its own membership even where interviews overlap. A canonical answer has grain (year, ID, variable). The analyst-facing table has one row per interview.

Python validates the JSON envelope, array alignment, respondent keys and scalar values. Load all files in a transaction. A file hash identifies unchanged content. The same filename with different bytes or two different answers for one interview and variable requires investigation. Keep source bytes immutable. A new cut may include additional fields. Missing properties and genuine survey missing codes have different meanings.

Use DuckDB because it supports SQL analytics and dbt in a single local file. The source schema retains raw payloads and file identity. A dbt staging view exposes membership. A decoded answer table joins labels to a versioned codebook. A respondent table brings common questions together for the six analyses. A seventh query audits overlap from membership. Full rebuilds are affordable for this volume. The runner loads, builds and tests with dbt, generates docs and runs SQL in that order. Stop at failure.

The design assumes column indices align in the Explorer export, code meanings are stable across these selected waves, and every original file remains available. If these assumptions fail, investigate before combining records. Descriptive results use observed answers and display denominators.

Local setup and the run command are in the [README](../README.md#run-it).

## Where the build diverged from this note

The initial note is preserved above. The final build differs in these ways:

- **Rebuild, not insert.** The runner builds a fresh candidate database from all reviewed sources, validates it through dbt and publishes the complete run through one atomic LATEST pointer. This trades a cheap full rebuild for straightforward recovery and a consistent database and results pair. The loader's insert-skip behaviour remains and is what its idempotence tests exercise.
- **More metadata than a codebook.** Profiling showed routing mattered more than expected, so wide projections, work-status meaning, ballot/form eligibility, wave counts and cut names also became seeds. `source_status` keeps the codebook's missing kind, and `status` can explain an excluded ballot/form combination.
- **Layers as schemas.** The note named a staging view and a decoded table. These became the `staging` and `marts` schemas, with seeds in `metadata`. `stg_membership` stays a view as planned.
- **A manifest.** Each run records inputs, definitions, counts and output hashes.

See profile.md, analyst-guide.md and production.md for coverage, interpretation and production assumptions.

## Validation boundaries

`source/failure_check.py` corrupts copies of the project and records which check stops each case; the result is in `report/failure-evidence.csv`. A bad extract fails the whole run instead of being quarantined, because silently dropping survey respondents would bias every estimate. No check rewrites a source response or converts an unknown to zero.

Seven interviews have unknown work status, so they remain in the respondent table but cannot enter the known-working or nonworking cohorts. Valid-looking equal-length columns that were misaligned upstream cannot be detected inside a wave held by one cut alone; the overlap comparison covers only the shared wave. Detecting that would need row-level provenance from the source.

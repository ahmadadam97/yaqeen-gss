# Design before implementation
Count interviews using (survey year, respondent ID). The waves are repeated cross sections. A raw file and its row number identify a source observation. Each file retains its own membership even where interviews overlap. A canonical answer has grain (year, ID, variable). The analyst-facing table has one row per interview.

Python validates the JSON envelope, array alignment, respondent keys and scalar values. Load all files in a transaction. A file hash identifies unchanged content. The same filename with different bytes or two different answers for one interview and variable requires investigation. Keep source bytes immutable. A new cut may include additional fields. Missing properties and genuine survey missing codes have different meanings.

Use DuckDB because it supports SQL analytics and dbt in a single local file. The source schema retains raw payloads and file identity. A dbt staging view exposes membership. A decoded answer table joins labels to a versioned codebook. A respondent table brings common questions together for the six analyses. A seventh query audits overlap from membership. Full rebuilds are affordable for this volume. The runner loads, builds and tests with dbt, generates docs and runs SQL in that order. Stop at failure.

The design assumes column indices align in the Explorer export, code meanings are stable across these selected waves, and every original file remains available. If these assumptions fail, investigate before combining records. Descriptive results use observed answers and display denominators.

Local setup and the run command are in the [README](../README.md#run-from-the-repository-root). The measured change from the planned membership view to a table is documented in the report.

# Design before implementation
Count interviews using (survey year, respondent ID). The waves are repeated cross sections. A raw file and its row number identify a source observation. Each file retains its own membership even where interviews overlap. A canonical answer has grain (year, ID, variable). The analyst-facing table has one row per interview.

Python validates the JSON envelope, array alignment, respondent keys and scalar values. Load all files in a transaction. A file hash identifies unchanged content. The same filename with different bytes or two different answers for one interview and variable requires investigation. Keep source bytes immutable. A new cut may include additional fields. Missing properties and genuine survey missing codes have different meanings.

Use DuckDB because it supports SQL analytics and dbt in a single local file. The source schema retains raw payloads and file identity. A dbt staging view exposes membership. A decoded answer table joins labels to a versioned codebook. A respondent table brings common questions together for the six analyses. A seventh query audits overlap from membership. Full rebuilds are affordable for this volume. The runner loads, builds and tests with dbt, generates docs and runs SQL in that order. Stop at failure.

The design assumes column indices align in the Explorer export, code meanings are stable across these selected waves, and every original file remains available. If these assumptions fail, investigate before combining records. Descriptive results use observed answers and display denominators.

Local setup and the run command are in the [README](../README.md#run-from-the-repository-root). The measured change from the planned membership view to a table is documented in the report.

## Current publication design after review

The initial note is preserved above. The current runner rebuilds a candidate database from all reviewed sources, validates it through dbt and publishes the complete run through one atomic LATEST pointer. This trades a cheap full rebuild for straightforward recovery and a consistent database/results pair. Source membership remains fully auditable. Wide projections, work-status meaning and ballot/form eligibility now come from seeds. source_status preserves the codebook missing kind; status can explain an excluded ballot/form combination. The run manifest records inputs, definitions, counts and output hashes. See profile.md, analyst-guide.md and production.md for coverage, interpretation and production assumptions.

## Current validation boundaries

The synthetic rejection lab is kept outside the submission repository. It confirms type/range, overlap, routing and publication checks, but also exposes conditional checks that are not yet implemented: positive web duration after USEWWW=NO, a combined duration above 168 hours, and observed split-item answers in an unknown ballot/form context. No minimum-coverage gate currently rejects an entirely unanswered reviewed source. Agree whether each condition should fail, warn or be quarantined before adding rules; do not rewrite source responses or convert unknowns to zero.

A read-only check of the submitted data found zero cases of the first three conditions. Seven interviews have unknown work status, so they remain in the general respondent table but cannot enter the known-working/nonworking cohorts. A reviewed checksum/count manifest cannot detect interviews omitted before review or valid-looking equal-length columns that were misaligned upstream. Those need independent source counts or row-level provenance.

# Inspection before modelling
The two independent NORC Explorer exports contain 32 fields each. A includes 2,538 interviews in 2014 and 2,867 in 2016. B includes those same 2,867 interviews and 2,348 in 2018. Every shared (year, id_) has identical answers. The union has 7,753 interviews, with no duplicate key inside either cut.

Each ZIP wraps batch_0.zip. Its result/GSS.json uses Python literal notation with single quotes, while result/post_processing_output.json is valid JSON and includes the codebook. We compared every row of both representations and found them equal in each archive. The committed files are the strict JSON members, byte for byte, renamed to identify their cut. Columns of equal length are aligned by array index. Respondent IDs repeat between waves.

[Full profile](profile.csv) gives counts, missing shares and raw status breakdowns for every field by year, counting the shared wave once. Raw labels distinguish .d (don't know), .n (no answer), .i (inapplicable) and .y (unavailable that year). Zero hours is a genuine answer. All selected concepts have some coverage in each of the three years. None requires filling a whole absent wave. POSTLIFE has no year-unavailable cases in these files.

NEWS, TVHOURS and the web module cover ballots A/B. INTTECH varies by ballot and form. SATJOB has a wording split in 2016. Missing answers cannot simply be interpreted as disinterest or dissatisfaction. For EVWORK, respondents who are working or unemployed and looking for work are outside its routing. Valid answers number 887, 1,023 and 816, respectively. The web duration requires both hours and minutes. An absent component leaves duration unknown. The gap between the intended population and the measured one is reported separately in the analyses.

## Follow-up coverage check

Valid answers as a percentage of all interviews, across all ballots:

| Variable | 2014 | 2016 | 2018 |
|---|---:|---:|---:|
| NEWS | 66.00 | 65.75 | 66.40 |
| TVHOURS | 65.76 | 65.68 | 66.23 |
| COMPUSE | 65.92 | 65.75 | 66.40 |
| WWWHR | 55.12 | 55.35 | 58.01 |
| INTTECH | 48.78 | 48.34 | 49.96 |

For the first four fields ballot C had zero valid responses in 863, 979 and 789 interviews, respectively, across the three waves. A/B assignment gives the opportunity to receive the media module. Within it, web-use routing and item nonresponse further narrow usable answers. Q4 also requires employment and a valid SATJOB answer. Q6 compares responding subsets on each measure and wave. [Ballot-level counts](../report/results/09_ballot_coverage.csv).

AGE, TVHOURS and WTSSPS arrive as JSON strings. WTSSNRPS arrives as a JSON number. The answer model decodes labelled endpoints such as zero hours before numeric conversion.

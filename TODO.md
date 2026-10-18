# TODO

Design intent lives in [docs/design](docs/design/README.md).

## Report section: when fair value could be reached

Added to the end of Valuation Summary rather than as an eleventh section, so the section list and numbering are unchanged. `scripts/check-report.ps1` checks that a horizon appears.

- [ ] Rerun WMT and check the horizon is consistent with the outcome table and that the quote did not set the outcomes or weights.

## Initiation by code

Initiation is now code, not an agent: SEC ticker list, Yahoo chart close, Treasury XML and Damodaran's workbook, with freshness checks in code. See [source acquisition](docs/design/valuation.md#source-acquisition).

- [ ] Rerun WMT end to end and check that Research uses the initiation record without searching for it again.
- [ ] If the Yahoo chart endpoint (unofficial) starts failing, the run stops at the source step; add a fallback quote source then, not before.

## Report and fair value database

- [ ] Store every report and its fair value estimates (each outcome's probability and per-share value, and the weighted fair value) in a database, keyed by ticker and run, so results can be queried and compared over time.

## Recurring analysis

Scheduled monitoring is currently out of scope in the [design overview](docs/design/README.md); update the design when this is taken on.

- [ ] Add recurring jobs that find companies without a recent analysis (by the age of the latest report in the database) and run the analysis for them.


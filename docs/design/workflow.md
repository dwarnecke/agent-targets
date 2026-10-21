# DCF Research Workflow

## Problem Statement

A successful model call does not make a company analysis complete or readable. The pipeline needs explicit handoffs and a self-contained report that states how a set of outcomes became a weighted company value.

## Proposed Solution

Fetch the initiation facts with code, then execute six agent stages in a fixed sequence in one conversation. Agents perform all business research, analysis and calculation, and keep each outcome's forecast schedules in [workbooks](#workbooks). Each stage's final message is saved as written as a record of that stage, and the final stage's response is the company report. The runner manages context, execution and storage, packs the workbooks, and fetches only the initiation facts.

## Technical Details

### Commands

```text
research WMT [--model <model-id>] [--effort <level>]
```

`research` is the project's only command. It starts a new company analysis in a new run directory and prints the final status and that directory, which holds `report.md` and every stage's response. The model defaults to `gpt-5.6-sol` and `--model` overrides it. The reasoning effort defaults to `xhigh` and `--effort` overrides it. There is no configuration file. Every change to prompts, policy, model, effort or inputs starts a new run.

Exit codes: `0` when the run completes with a report, `2` for invalid usage, `3` when an initiation source fails (before any model call) or a stage returns no response within its attempts.

### Stage contracts

The six agent stages share one conversation and see each other's work directly, so no stage's document is needed for handoff. The saved `<stage>.md` files are a review record, and only the report is prescribed as a document. The [run lifecycle](execution.md#run-lifecycle) governs invocation. Modeling, refutation, comparison and review each end with an outcome table so the exact probabilities and per-share values survive any context compaction.

| Stage ID | Responsibility | Final message |
|---|---|---|
| `initiation` | Code fetches the security, quote and published rate observations and checks rate freshness | The initiation record |
| `research` | Investigate the business and candidate outcomes, set outcomes and probabilities, calculate the hurdle | Outcomes, partition rule, probabilities, hurdle, the outside topics investigated with their dispositions, including management's own forward statements, evidence and limitations |
| `modeling` | Research the numerical inputs for each outcome and build its forward DCF in the workbooks | Per-outcome valuation summary with the justification of any period-1 figure that departs from guidance, run rate or management targets, an outcome table, the workbook tabs written, evidence and limitations |
| `refutation` | Attempt to disprove the claims, distribution and economics, recompute each outcome, then apply the calculation errors it reproduced and the material findings the evidence supports | Findings with dispositions, signed per-share effects and whether each was applied, per-outcome checks, the joint sensitivity of the effects not applied, the corrected outcome table, a change log and the workbook tabs it changed |
| `comparison` | Investigate outside disagreements and apply adopted discrepancies that primary evidence supports | Discrepancy decisions with estimated effects, evidence and coverage gaps, a diagnostic convention bridge for each outside fair value, each outside-identified outcome mapped to an outcome or flagged as missing or under-argued, the outcome table after changes, a change log and the workbook tabs it changed |
| `review` | Recompute every changed or added outcome, check the outcome table and change logs, and fix small errors | The final outcome table and weighted value, the errors fixed, larger problems left with signed effects, and the workbook tabs it changed |
| `report` | Reconcile everything and calculate the weighted values | The ten-section company report, saved as `report.md` |

Research fixes the outcomes and probabilities before any DCF exists, and modeling keeps them. Refutation and comparison may change the outcomes, probabilities and valuations, only for a sourced finding or adopted discrepancy or a defect in the partition. A revised set meets the research requirements for outcomes again. The quote, outside price targets and the resulting values never justify a change. The review fixes small errors in the corrections and reports larger problems without changing them. The report takes the review's final outcome table as the headline, presents each finding once with whether it was applied, and shows a review-adjusted weighted value beside the headline as a sensitivity built only from the effects not applied. The report stage also receives the saved initiation record, the responses of the five earlier agent stages and the evaluated workbooks in its prompt.

The quote is a reporting and timing reference, never a source for assumptions. Reverse DCF is excluded.

### Workbooks

Each outcome's forecast lives in its own workbook, so a reader or a later stage can open one outcome's statements without the others, and the schedules survive context compaction. Every workbook looks forward: its statements hold an opening column and periods 1 to 10, and history appears only in the company workbook's trailing-twelve-month baseline and the period-1 reference points in `Revenue`. The agents' shell cannot write `.xlsx` files, so an agent writes one tab-separated text file per tab, `model/company/Inputs.tsv` or `model/<outcome ID>/<Tab>.tsv`, and the runner packs each directory into `model/<book>.xlsx` after every stage. Modeling creates the files; later stages edit the files of the outcomes they change in place. A new outcome gets a new directory, and a retired one is renamed with a `-retired` suffix and named in the change log.

| Book | Tabs |
|---|---|
| Company, in `model/company/` | `Inputs` |
| Going-concern outcome | `Inputs`, `Revenue`, `Income`, `Balance`, `CashFlow`, `Value`, `Tests` |
| Outcome valued on restructuring, default or liquidation | `Inputs`, `Recovery`, `Tests` |

- **Company `Inputs`:** the hurdle `r` with its components, the share count, the minimum operating cash, the opening operating balance sheet, the trailing-twelve-month baseline with its three filing figures, the period dates and the assumption register (definition, units, period, value, outcomes it applies to, evidence and uncertainty).
- **Outcome `Inputs`:** the company values the outcome uses, repeated as numbers, and its own scalar assumptions, each tagged with its register entry.
- **`Revenue`:** the segment driver build and the period-1 comparison with guidance, the latest quarter's run rate and management targets.
- **`Income`:** revenue to normalized net income attributable to common.
- **`Balance`:** the operating balance sheet, described in the [valuation conventions](valuation.md#statement-conventions).
- **`CashFlow`:** the owner-cash-flow bridge and owner funding of shortfalls, with check rows tying net income, capex and working capital to `Income` and `Balance`.
- **`Value`:** discounting, terminal value, return on new capital, excess assets, equity value, the per-share value with its zero floor and the unfloored value, and the rate sensitivities at base and base ±100 bp as three discounting rows.
- **`Tests`:** the partition rule's tests, thresholds, the path's value at each named period end, and pass or fail.
- **`Recovery`:** pre-event receipts, the claims waterfall, the common recovery and the per-share value.

Layout and cell rules keep the files uniform and checkable:

- `Revenue`, `Income`, `Balance`, `CashFlow`, `Value` and `Recovery` share one layout: row 1 is the header `Item`, `Unit and source`, `Opening`, `P1` to `P10` in columns A to M, row 2 holds each period's end date, and a scalar result sits in column C. `Inputs` and `Tests` are free-form.
- On `Inputs` a scalar is its label in column A and its value in column C. A company value repeated on an outcome's `Inputs` keeps the company row's label, so a difference between them can be found.
- Amounts are USD millions, shares are millions, per-share values are dollars.
- A cell is a number, text or a formula beginning with `=`. Formulas use `+ - * / ^`, comparisons, cell and range references within the book (`C5`, `Revenue!D7`, `'Net income'!D7`, `D5:M5`) and `SUM`, `SUMPRODUCT`, `MIN`, `MAX`, `ABS`, `AVERAGE`, `ROUND` and `IF`. There are no external links, no circular references (interest uses opening balances) and no macros.
- Scalar assumptions sit on `Inputs`; a period-by-period driver sits on the tab it drives; every other cell is a formula.
- A row whose label begins `Check` is 0 in every period. The per-share value is column C of the row labeled `Fair value per share` in `Value` or `Recovery`.

The runner evaluates each formula and stores its result beside it, so viewers that do not recalculate show values. It also saves the evaluated tabs as text in `model/values.md`, which later stages read to compare a workbook's values with their own recomputation, and the report stage receives the same text in its prompt. A formula it cannot evaluate, an unreadable file, a tab or book name it cannot use or a reference to a missing tab is saved to `model/problems.md` and left without a value; the next stage reads that file first and repairs the files it owns, and the report stage receives it with the evaluated tabs. The runner does not judge the values. `scripts/check-model.ps1` reports the packing problems, the `Check` rows that are not 0, any outcome `Inputs` value that differs from the company row with the same label, and each outcome's per-share value for comparison with the outcome table.

### Primary report

The report begins with a metadata block (company and security, valuation and quote date, currency and share basis) followed by ten sections in order.

| ID | Section | Required content |
|---|---|---|
| P1 | Valuation Summary | A table of every outcome by a short recognizable name, probability and per-share fair value only, with no weighted-contribution or other derived column, and the weighted fair value stated in the sentence introducing the table, then the quote and where it falls against the modeled range, main drivers, uncertainties and limitations, then how long the price could take to reach the weighted fair value: a horizon range based on when the value-driving cash flows show up in reported results, the catalysts that close the gap, the outcomes that would take longer or never converge, and what would invalidate the horizon |
| P2 | Business Overview | How the company earns money and the few drivers of owner cash flow |
| P3 | Competitive Moat | Each moat by bucket with benefit, barrier, durability class, end condition and forecast effect (evidence classified as not a moat is omitted); evidence against durability by erosion channel; the implications for each outcome's forecast |
| P4 | Financial Analysis | Reconciled baseline, earnings quality, working capital, capex, SBC, debt and funding |
| P5 | Outcome Formation | How research produced distinct outcomes, the partition rule and probability judgments, and any change made after review with its evidence |
| P6 | Valuation Approach | Cash-flow basis, timing, share count, terminal economics, rate observations and hurdle |
| P7 | Outcome Distribution | A table of every outcome with the explanation of each |
| P8 | Risks and Sensitivities | Contrary evidence, refutation and review findings with dispositions, whether each was applied and signed per-share effects, the review-adjusted value, rate sensitivities |
| P9 | External Comparisons | Discrepancies and decisions, whether each was applied, or that none were available |
| P10 | Sources and Calculations | Source register, schedules, discount and terminal workings and independent checks |

There is no fixed page count or scenario count. Legitimately unavailable content gets an explicit explanation. Dedicated trading recommendations and charts are unnecessary. Report structure follows [CFA Institute's report guidance](https://www.cfainstitute.org/sites/default/files/-/media/documents/support/research-challenge/challenge/rc-equity-research-report-essentials.pdf); moat analysis follows [Morningstar's moat framework](https://www.morningstar.com/investing-definitions/economic-moat), extended and tested as described in [competitive advantage classification](valuation.md#competitive-advantage-classification).

### Outcome data

The outcome table has one row per outcome with its ID, name, meaning, unconditional probability and per-share value. The Valuation Summary repeats it by name, probability and value only. The report agent calculates the weighted value using the [weighting rules](valuation.md#outcome-weighting). The report presents outcome values, the weighted value and the quote rounded to the nearest whole dollar, review effects under five dollars to the cent, and aggregates to two decimals in billions, without printing unrounded values or arithmetic chains; calculations keep full precision. The headline is the weighted value of the review's final outcome table, changed only by a calculation error the review reproduced and left uncorrected; every other finding not applied is a sensitivity.

## Failure Handling

The runner fails a run when an initiation source cannot be read or is too old, or when a stage returns no response. Unresolved questions, missing evidence and disagreements in the analysis are disclosed in the stage documents and carried into the report. Every attempt directory and every accepted response is kept, and a retry is a new run.

## Validation

Test the initiation parsers and freshness checks with saved source responses, and the stage order, handoff, workbook packing and report persistence with a fake backend. Review a real report as described in the [overview](README.md#validation), and check its workbooks with `scripts/check-model.ps1`.

## Not Implemented

- DOCX/PDF exports and charts. Markdown is the saved review document, and the workbooks are its supporting schedules.
- Live workbook links between outcomes, a workbook summary tab and a debt schedule tab. The outcome table stays in the stage records and constant debt is rows in `Income` and `Balance`.

## Open Questions

- Which research model reliably completes every stage?
- Do the longer refutation and comparison stages finish within the call timeout when they rebuild an outcome?
- What report and context sizes keep the schedules complete, now that the report prompt carries the evaluated workbooks?
- Does the first company pilot show content that does not fit the ten sections?
- Can the agents write correct tab files and formulas with the constrained PowerShell shell, and is the fixed tab set enough for each outcome?

## References

- [Project overview](README.md)
- [Valuation](valuation.md)
- [Execution](execution.md)
- [CFA Institute: Equity Valuation Applications and Processes](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-applications-and-processes)

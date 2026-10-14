# DCF Research Workflow

## Problem Statement

A successful model call does not make a company analysis complete or readable. The pipeline needs explicit handoffs and a self-contained report that states how a set of outcomes became a weighted company value.

## Proposed Solution

Execute six stages in a fixed sequence in one conversation. Agents perform all source discovery, analysis and calculation. Each stage's final message is saved as written as a record of that stage, and the final stage's response is the company report. The runner manages context, execution and storage only.

## Technical Details

### Commands

```text
research WMT [--model <model-id>] [--effort <level>]
```

`research` is the project's only command. It starts a new company analysis in a new run directory and prints the final status and that directory, which holds `report.md` and every stage's response. The model defaults to `gpt-5.6-sol` and `--model` overrides it. The reasoning effort defaults to `xhigh` and `--effort` overrides it. There is no configuration file. Every change to prompts, policy, model, effort or inputs starts a new run.

Exit codes: `0` when the run completes with a report, `2` for invalid usage, `3` when a stage returns no response within its attempts.

### Stage contracts

All six stages share one conversation and see each other's work directly, so no stage's document is needed for handoff. The saved `<stage>.md` files are a review record, and only the report is prescribed as a document. The [run lifecycle](execution.md#run-lifecycle) governs invocation. Modeling ends with an outcome table so the exact probabilities and per-share values survive any context compaction.

| Stage ID | Responsibility | Final message |
|---|---|---|
| `initiation` | Resolve security, quote and published rate observations | Findings and checks |
| `research` | Investigate the business and candidate outcomes, set outcomes and probabilities, calculate the hurdle | Outcomes, partition rule, probabilities, hurdle, evidence and limitations |
| `modeling` | Research the numerical inputs for each outcome and build its forward DCF | Per-outcome valuation and an outcome table, evidence and limitations |
| `refutation` | Attempt to disprove the claims, distribution and economics, and recompute each outcome | Findings with dispositions, signed per-share effects, per-outcome checks and limitations |
| `comparison` | Investigate outside disagreements | Discrepancy decisions with estimated effects, evidence and coverage gaps |
| `report` | Reconcile everything and calculate the weighted values | The ten-section company report, saved as `report.md` |

Research fixes the outcomes and probabilities before any DCF exists. Later stages keep them and never reweight after seeing values or the quote. The refutation reports findings without editing the model. The report presents them once, uses the refutation's corrected value where it shows a calculation error, and shows a review-adjusted weighted value beside the headline as a sensitivity built from the effects the refutation computed. The report stage also receives the saved responses of the five earlier stages in its prompt.

The quote is a reporting and timing reference, never a source for assumptions. Reverse DCF is excluded.

### Primary report

The report begins with a metadata block (company and security, valuation and quote date, currency and share basis) followed by ten sections in order.

| ID | Section | Required content |
|---|---|---|
| P1 | Valuation Summary | A table of every outcome by a short recognizable name, probability and per-share fair value ending with the weighted fair value, then the quote and where it falls against the modeled range, main drivers, uncertainties and limitations |
| P2 | Business Overview | How the company earns money and the few drivers of owner cash flow |
| P3 | Competitive Moat | Evidence for and against durable advantages and the implications for the forecast |
| P4 | Financial Analysis | Reconciled baseline, earnings quality, working capital, capex, SBC, debt and funding |
| P5 | Outcome Formation | How research produced distinct outcomes, the partition rule and probability judgments |
| P6 | Valuation Approach | Cash-flow basis, timing, share count, terminal economics, rate observations and hurdle |
| P7 | Outcome Distribution | A table of every outcome with the explanation of each |
| P8 | Risks and Sensitivities | Contrary evidence, refutation findings with dispositions and signed per-share effects, the review-adjusted value, rate sensitivities |
| P9 | External Comparisons | Discrepancies and decisions, or that none were available |
| P10 | Sources and Calculations | Source register, schedules, discount and terminal workings and independent checks |

There is no fixed page count or scenario count. Legitimately unavailable content gets an explicit explanation. Dedicated trading recommendations and charts are unnecessary. Report structure follows [CFA Institute's report guidance](https://www.cfainstitute.org/sites/default/files/-/media/documents/support/research-challenge/challenge/rc-equity-research-report-essentials.pdf); moat analysis follows [Morningstar's moat framework](https://www.morningstar.com/investing-definitions/economic-moat).

### Outcome data

The outcome table has one row per outcome with its ID, name, meaning, unconditional probability and per-share value. The Valuation Summary repeats it by name, probability and value only. The report agent calculates the weighted value using the [weighting rules](valuation.md#outcome-weighting). The report presents outcome values, the weighted value and the quote rounded to the nearest whole dollar, review effects under five dollars to the cent, and aggregates to two decimals in billions, without printing unrounded values or arithmetic chains; calculations keep full precision. The headline is the weighted value of modeling's outcome values, changed only by a finding the review labeled a calculation error; every other finding is a sensitivity.

## Failure Handling

The runner fails a run only when a stage returns no response. Unresolved questions, missing evidence and disagreements are disclosed in the stage documents and carried into the report. Every attempt directory and every accepted response is kept, and a retry is a new run.

## Validation

Test the stage order, handoff and report persistence with a fake backend. Review a real report as described in the [overview](README.md#validation).

## Not Implemented

- DOCX/PDF exports, charts and workbook generation. Markdown is the saved review document.

## Open Questions

- Which research model reliably completes every stage?
- What report and context sizes keep the schedules complete?
- Does the first company pilot show content that does not fit the ten sections?

## References

- [Project overview](README.md)
- [Valuation](valuation.md)
- [Execution](execution.md)
- [CFA Institute: Equity Valuation Applications and Processes](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-applications-and-processes)

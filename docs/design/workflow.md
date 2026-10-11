# DCF Research Workflow

## Problem Statement

A successful model call does not make a company analysis complete or readable. The pipeline needs explicit handoffs and a self-contained report that states how a set of outcomes became a weighted company value.

## Proposed Solution

Execute six stages in a fixed sequence. Agents perform all source discovery, analysis and calculation. Each stage returns a Markdown document, the next stage receives it as written, and the final stage's document is the company report. The runner manages context, execution and storage only.

## Technical Details

### Commands

```text
research WMT [--model <model-id>]
```

`research` is the project's only command. It starts a new company analysis in a new run directory and prints the final status and that directory, which holds `report.md` and every stage's response. The model defaults to `gpt-6-astra` and `--model` overrides it; there is no configuration file. Every change to prompts, policy, model or inputs starts a new run.

Exit codes: `0` when the run completes with a report, `2` for invalid usage, `3` when a stage returns no response within its attempts.

### Stage contracts

Every stage receives the ticker and the responses of its predecessors. The [run lifecycle](execution.md#run-lifecycle) governs invocation and handoff.

| Stage ID | Responsibility | Deliverable |
|---|---|---|
| `initiation` | Resolve security, quote and published rate observations | Security, quote, rates, sources and checks |
| `research` | Investigate the business and candidate regimes, set states and probabilities, calculate the hurdle | Baseline, regimes and states, partition rule, probabilities, regime research, alternatives, discount rate, evidence and limitations |
| `modeling` | Research the numerical inputs for each state and build its forward DCF | Per-state assumptions, schedules, terminal values and per-share values, a state table, evidence and limitations |
| `refutation` | Attempt to disprove the claims, distribution and economics, and recompute each state | Evidence, distribution and model reviews, per-state checks, findings and limitations |
| `comparison` | Investigate outside disagreements | Discrepancy decisions, evidence and coverage gaps |
| `report` | Reconcile everything and calculate the weighted values | The ten-section company report, saved as `report.md` |

Research fixes the states and probabilities before any DCF exists. Later stages keep them and never reweight after seeing values or the quote. The refutation reports findings without editing the model; the report presents them and, where the refutation shows a calculation error, uses its corrected value and says so.

The quote is a reporting and timing reference, never a source for assumptions. Reverse DCF is excluded.

### Primary report

The report begins with a metadata block (company and security, valuation and quote date, currency and share basis) followed by ten sections in order.

| ID | Section | Required content |
|---|---|---|
| P1 | Valuation Summary | Weighted fair value per share, the quote, modeled range, main drivers, uncertainties and limitations |
| P2 | Business Overview | How the company earns money and the few drivers of owner cash flow |
| P3 | Competitive Moat | Evidence for and against durable advantages and the implications for the forecast |
| P4 | Financial Analysis | Reconciled baseline, earnings quality, working capital, capex, SBC, debt and funding |
| P5 | Outcome Formation | How research produced distinct regimes and states, the partition rule and probability judgments |
| P6 | Valuation Approach | Cash-flow basis, timing, share count, terminal economics, rate observations and hurdle |
| P7 | Outcome Distribution | A table of every state and a table of every regime with the explanation of each |
| P8 | Risks and Sensitivities | Contrary evidence, refutation findings and their handling, rate sensitivities |
| P9 | External Comparisons | Discrepancies and decisions, or that none were available |
| P10 | Sources and Calculations | Source register, schedules, discount and terminal workings and independent checks |

There is no fixed page count or scenario count. Legitimately unavailable content gets an explicit explanation. Dedicated trading recommendations and charts are unnecessary. Report structure follows [CFA Institute's report guidance](https://www.cfainstitute.org/sites/default/files/-/media/documents/support/research-challenge/challenge/rc-equity-research-report-essentials.pdf); moat analysis follows [Morningstar's moat framework](https://www.morningstar.com/investing-definitions/economic-moat).

### Outcome data

The state table has one row per terminal state with its ID, regime, meaning, unconditional joint probability and per-share value; the regime table has one row per regime with its member states, probability, conditional value and contribution. The report agent calculates these using the [weighting rules](valuation.md#outcome-and-regime-weighting). A missing value is stated with its reason, and the aggregates that depend on it are reported as unavailable.

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

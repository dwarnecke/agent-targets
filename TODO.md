# TODO

Written 2026-10-10. Target dates are planning estimates; slide them, but keep the order. Design intent lives in [docs/design](docs/design/README.md); this file only tracks what to do next.

## Where things stand

- Pipeline is implemented. One full WMT run exists ([runs/WMT-20261010T225810Z-9372](runs/WMT-20261010T225810Z-9372/report.md)); 15 other tickers have only an `initiation.md`.
- No reviewed full run yet, so the design's open questions (model, timeout, attempt limits) are still unanswered.
- WMT result: weighted fair value **$25.10** (state range $10.47 to $39.05) against a **$111.35** quote, about 77% below. Not yet known whether that is a real finding or an artefact of the method.
- Observed cost: one WMT run took about 13 min end to end (initiation under 1, research about 3, modeling about 4, refutation about 3, comparison under 1, report about 2). Fifteen parallel initiations took about 4 min each. No stage hit the 10-minute timeout.
- Rate retrieval is inconsistent across agents. The WMT run used a Treasury 10Y of 5.28% dated Oct 2 (8 days old, over the 7-day limit). The batch run used 5.24% dated Oct 9. ERP was 4.20% everywhere. Same prompt, different captured row, so retrieval is not reproducible.

## Goal and exit criteria

"Reached the fair value estimate" means one company report that a human reviewer accepts under the [Validation](docs/design/README.md#validation) rule:

1. Every key claim traces to a primary source.
2. The weighted value recomputes from the report's state table.
3. The quote and outside targets did not set states or weights.
4. The Treasury and ERP inputs came from a deterministic fetch, not the model.

## Timeline

| Target | Milestone | Done when |
|---|---|---|
| Oct 12-14 | Diagnose the WMT $25.10 gap | Written note: which of rate, FCFE convention, capex normalization, share basis or probabilities drives it, and whether it is a bug or a defensible view |
| Oct 12-17 | Deterministic rates (see below) | `research WMT` gets both rates from code; tests pass; design docs updated |
| Oct 15-24 | Prompt iteration rounds (see below) | Two consecutive reruns of WMT give the same states and a value within an agreed tolerance |
| Oct 24-28 | Pilot on 3 to 5 tickers | Reviewed reports for a mix (for example WMT, MSFT, one cyclical, one with complex financing) |
| Oct 28-31 | Settle open questions | Model, timeout and attempt limits chosen from pilot data and written into [execution.md](docs/design/execution.md) |
| Oct 31 | First reviewed fair value estimate | Exit criteria above met for at least one company; README says a reviewed run exists |

Slip rule: if the WMT diagnosis shows a method flaw (not just a prompt flaw), stop and fix the design docs before the prompt rounds.

## 1. Retrieve the 10Y and ERP without the AI

Why: the model picks different observation dates run to run, and freshness policy is judged by the same model that fetched the data. Rates are two numbers with official machine-readable sources, so they do not need an agent.

- [ ] Treasury 10Y: read the nominal Daily Treasury Par Yield Curve XML feed from the [feed directory](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/interest-rate-xml-files). Select the latest dated record and the `BC_10YEAR` element by name, never by position. Check the exact element name against a live response before coding.
- [ ] Damodaran ERP: find a stable machine-readable source for the monthly "Trailing 12 month, with adjusted payout" series (his data files, or the home-page panel). Verify which one carries the correct series and date; fall back to parsing the panel only if no file does. This is the fragile part.
- [ ] Optional cross-check: FRED `DGS10` for the Treasury figure. Treat a mismatch as a warning, not a replacement.
- [ ] Compute age at capture in code. Keep the 7-day (Treasury) and 45-day (ERP) limits, and record the retrieval time and source URL.
- [ ] Inject a rates record into the Initiation prompt (or skip the agent's rate step) so Research still computes `r` from it. Decide whether the runner or the agent calculates `r`; the runner doing it removes one more model arithmetic step.
- [ ] Failure behavior: decide whether an unreachable or stale source ends the run (new exit code) or is disclosed and the run continues. The current design says analytical problems never stop a run; a fetch failure is closer to an infrastructure failure, so it likely should. Settle this before coding.
- [ ] Tests: fixture responses for both sources (normal, stale, missing 10Y column, renamed series); no live network in the suite.
- [ ] Docs: [design README](docs/design/README.md) and [valuation.md](docs/design/valuation.md#source-acquisition) currently say the runner has no source integration. Update them and the `prompts/initiation.md` rate bullets together.
- [ ] Cache one rates record per day so a batch of tickers shares the same inputs.

Timeline: Oct 12-13 spike and source check; Oct 14-16 implement and test; Oct 17 docs and one live WMT run.

## 2. Further prompt engineering

Work from evidence in the saved runs, one change per round, rerun WMT each time and diff the report.

- [ ] Quote source: initiation took the close from Investing.com because the Nasdaq page returned no data. Decide whether a secondary source is acceptable, and say so in the prompt.
- [ ] Share basis: the report calls 7.961B diluted shares a "dated approximation". Tighten how the basis is derived and dated.
- [ ] Zero-net-borrowing convention: the report says it does not fit Walmart's actual financing and strains the adverse state. Revisit the FCFE instructions in `prompts/modeling.md` and `prompts/common.md`.
- [ ] Capex normalization: the terminal cash flow jumps in S2 and S3 without disclosure support. Require modeling to justify terminal capex against history, or cap the uplift.
- [ ] Hurdle level: 5.28% + 4.20% = 9.48% for a low-beta retailer. Confirm this is intended before treating the low value as a finding (design says no beta or size adjustment).
- [ ] Refutation and Report: confirm the report recomputes the weighted value from the table and that refutation values are actually used, not just quoted.
- [ ] Stability: rerun the same ticker three times; list what changes (states, probabilities, per-state values) and tighten the instructions that allow the drift.
- [ ] Breadth: run the 15 existing tickers through all stages after rates are fixed, then sort failures by stage and by company type (financing, foreign currency, pre-revenue like NTLA, ADR like SAP and TCEHY). Scope is currently USD common equity, so some of these may need to be declared out of scope instead.
- [ ] Keep detailed rules in the prompts and docs, not here.

Timeline: three rounds, roughly Oct 15-17, Oct 20-22, Oct 23-24. Stop a round early if two reruns agree.

## 3. Housekeeping

- [ ] Decide what to do with the 15 initiation-only run directories in `runs/` (keep as rate-consistency evidence for now, delete after rates are deterministic).
- [ ] Record timeout and cost per stage in the pilot so [Open Questions](docs/design/README.md#open-questions) can be closed with data.
- [ ] After each milestone, update the README status sentence ("a reviewed full company run has not been completed").

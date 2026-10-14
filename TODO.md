# TODO

Design intent lives in [docs/design](docs/design/README.md).

## Report section: when fair value could be reached

Add a report section on how long the price could take to reach the weighted fair value, and what would get it there.

- [ ] Add the section to the report. This needs a new row in the report contract in [workflow.md](docs/design/workflow.md#primary-report) and a matching line in `prompts/report.md` (the report is currently ten sections; decide whether this is an eleventh or part of Valuation Summary).
- [ ] Content: an expected horizon (a range, not a point), the catalysts that close the gap, and which outcomes would take longer or never converge.
- [ ] Base the horizon on the company's economics, such as when the cash flows that drive the value show up in reported results. The quote may be the gap to close, but it must not set the outcomes or weights, and reverse DCF stays excluded.
- [ ] State the uncertainty plainly. Market convergence is not guaranteed, so say what would invalidate the horizon.
- [ ] Rerun WMT and check the section is consistent with the outcome table.

## Non-AI 10Y and ERP

Why: the same prompt gave a 5.28% (Oct 2) 10Y in one run and 5.24% (Oct 9) in another.

- [ ] Treasury 10Y: read the official Daily Treasury Par Yield Curve XML feed and select the 10-year element by name.
- [ ] ERP: find a machine-readable source for Damodaran's "Trailing 12 month, with adjusted payout" series. Parse the home-page panel only if no file carries it.
- [ ] Keep the 7-day and 45-day freshness limits, checked in code. Decide whether a failed or stale fetch ends the run.
- [ ] Pass the rates into the Initiation prompt and update `prompts/initiation.md` and the design docs that say the runner has no source integration.
- [ ] Test with fixture responses, not live network.

## Prompt engineering

One change per round; rerun WMT and diff the report.

- [ ] Zero-net-borrowing convention: the WMT report says it strains the adverse outcome.
- [ ] Terminal capex: cash flow jumps in S2 and S3 without disclosure support.
- [ ] Share basis: the report calls 7.961B diluted shares a "dated approximation".
- [ ] Quote source: decide if a secondary source (Investing.com) is acceptable.
- [ ] Stability: rerun WMT three times and tighten whatever drifts.

# Common Analytical Policy

This policy applies to every stage. Each stage is a fresh call: your final message is the stage's complete deliverable, written as Markdown, and the next stage receives it as written. Do not end with a question or ask for input; nobody is available to answer. Put everything the next stage needs in your final message, not in earlier messages.

## Evidence

- Read primary sources, not search snippets. Cite each source by publisher, title, URL or filing, a precise locator (page, section or table) and retrieval time, and say whether a figure is a sourced fact, a derived amount or a judgment.
- Never invent a value. If something cannot be established, say so, state what is missing and why it matters, and continue with the analysis that is still possible. Do not stop, and do not hide the gap behind a plausible number.
- Where evidence contradicts an assumption, say so and show how you resolved it.

## Discount rate

```text
r = treasury_10y_decimal + implied_erp_decimal
```

Convert the published percentages to decimals and add them with no intermediate rounding. No company beta, size premium or discretionary spread is added. Use this one `r` for every forecast, discount and terminal calculation in the run.

## Calculation tools

Your shell is PowerShell in a read-only sandbox with no `python`, running in constrained language mode. Use it for every calculation that matters. Plain `[decimal]` arithmetic (`+ - * /`) keeps full precision. Method calls such as `[math]::Pow` are rejected, so build discount factors by repeated multiplication, for example `$f = [decimal]1; 1..5 | ForEach-Object { $f = $f * (1 + $r) }`. Run the arithmetic rather than doing it mentally, and show the results. Test a small known calculation first. If the tool keeps failing, say so and show your manual work.

## Cash-flow conventions

These conventions are the accepted policy for the first supported case. Do not treat them as defects, but do point out where the evidence cannot support them.

- Start from net income attributable to common shareholders, which is already after interest, minority claims and SBC expense. Do not add SBC back and never subtract it a second time.
- Constant diluted share count, no buyback accretion, no new equity. Use the latest filing's cover-page shares outstanding plus dilutive securities, taken as that filing's weighted-average diluted shares minus its weighted-average basic shares. State both dates. No filing gives an exact valuation-date diluted count, so this dated approximation is accepted.
- Zero net borrowing with sustainable refinancing of existing debt. Debt issuance and repayment, acquisitions and dividends are not separate forecast items. If the evidence shows a need for borrowing, acquisitions or outside funding that this contradicts, say so.
- Excess assets are only amounts shown to be distributable beyond operating liquidity, restricted or trapped balances and funding needs.
- Twelve-month forward periods from the valuation date with end-of-period receipts, and the same convention for terminal value.

## Outcomes

- The pipeline runs initiation, research, modeling, refutation, comparison and report in that order. Research establishes the outcomes and their probabilities before any DCF is built; modeling values them; a fresh refutation call challenges the result.
- Regimes are distinct business mechanisms with observable conditions that company evidence supports. A generic ladder of large failure, small failure, expected and large success, renamed bull/base/bear cases and uniform growth or margin shifts are not regimes.
- Terminal states are mutually exclusive, jointly exhaustive complete paths with unconditional joint probabilities that sum to 1. A cross-cutting factor such as a macro, regulatory, cyber or international shock is a condition inside the states it affects, not its own state. Do not infer missing probabilities, assume equal weights, or normalize a bad total.
- The market quote is a reporting reference only. Never use it, outside price targets or a desired result to choose outcomes, probabilities or assumptions, and never run a reverse DCF. Once research sets the outcomes and probabilities, later stages keep them and do not reweight after seeing values. If new evidence contradicts them, say so prominently and keep them.

## Limitations

Disclose every limitation, unresolved question and disagreement plainly in your deliverable, so that the report can carry it to the reader. A limitation is a statement in the analysis, never a reason to stop.

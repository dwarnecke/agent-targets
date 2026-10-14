# Common Analytical Policy

This policy applies to every stage. All six stages continue one conversation, so you keep what you read and calculated in earlier stages and need not repeat it. Each stage's final message is saved as its record; do not end with a question, because nobody is available to answer. Only the report must stand alone for a reader who sees nothing else.

## Math notation

Write every equation in LaTeX so it renders in common viewers: `$...$` inline, `$$...$$` on their own lines for display, never `\(...\)` or `\[...\]`. Write a literal dollar amount as `\$`, such as `\$281.55`. Keep `|` out of math inside tables. Plain arithmetic such as `25.97 - 11.71` may stay as text.

## Evidence

- Read primary sources, not search snippets. Cite each source by publisher, title, URL or filing, a precise locator (page, section or table) and retrieval time, and say whether a figure is a sourced fact, a derived amount or a judgment.
- Never invent a value. If something cannot be established, say so, state what is missing and why it matters, and continue with the analysis that is still possible.
- Where evidence contradicts an assumption, say so and show how you resolved it.
- Disclose every limitation, unresolved question and disagreement plainly in your final message, so the report can carry it to the reader.

## Discount rate

```text
r = treasury_10y_decimal + implied_erp_decimal
```

Convert the published percentages to decimals and add them with no intermediate rounding. No company beta, size premium or discretionary spread is added. Use this one `r` for every forecast, discount and terminal calculation in the run. The only other rates are the required base ±100 bp sensitivities, which perturb `r` to show its effect.

## Calculation tools

Your shell is PowerShell in a read-only sandbox with no `python`, running in constrained language mode. Use it for every calculation that matters. Plain `[decimal]` arithmetic (`+ - * /`) keeps full precision. Method calls such as `[math]::Pow` are rejected, so build discount factors by repeated multiplication, for example `$f = [decimal]1; 1..5 | ForEach-Object { $f = $f * (1 + $r) }`. Show the results. Test a small known calculation first. If the tool keeps failing, say so and show your manual work.

## Cash-flow conventions

These conventions are the accepted policy for the first supported case. Do not treat them as defects, but do point out where the evidence cannot support them.

- Start from net income attributable to common shareholders, which is already after interest, minority claims and SBC expense. Do not add SBC back.
- Constant diluted share count with no buyback accretion: the best-supported count at the valuation date, such as the latest filing's cover-page shares outstanding plus dilutive securities, with its source and date.
- Zero net borrowing with sustainable refinancing of existing debt. Debt issuance and repayment, acquisitions and dividends are not separate forecast items. If the evidence shows a need for borrowing, acquisitions or outside funding that this contradicts, say so.
- An outcome whose mechanism is restructuring, default or liquidation is valued on that mechanism: pre-event receipts plus the common recovery the evidence supports, which may be zero as a labeled judgment.
- Each outcome's value is its representative path, the most central one the evidence supports within the outcome. The probability-weighted total is a scenario value, not a statistical expectation.
- Negative owner cash flow is valued like any other flow: owners are assumed to fund a shortfall at the hurdle rate, with no change in the share count. Common equity is worth at least zero.
- Excess assets are cash and investments above a stated minimum operating balance (a labeled judgment from historical cash levels and scale), excluding restricted or trapped amounts, added to equity value at their amount with the income they earn removed from the forecast. Shortfalls are charged to owners at the hurdle rate, so this cash is not also reserved for them.
- Twelve-month forward periods from the valuation date with end-of-period receipts, and the same convention for terminal value. The explicit forecast is ten such periods, followed by the terminal value, except for an outcome valued on a restructuring, default or liquidation mechanism.

## Outcomes

- Research establishes the outcomes and their probabilities before any DCF is built; later stages keep them and do not reweight after seeing values.
- Outcomes are distinct business mechanisms with observable conditions that company evidence supports. A generic ladder of large failure, small failure, expected and large success, renamed bull/base/bear cases and uniform growth or margin shifts are not outcomes.
- Outcomes are mutually exclusive, jointly exhaustive complete paths with unconditional probabilities that sum to 1. A cross-cutting factor such as a macro, regulatory, cyber or international shock is a condition inside the outcomes it affects, not its own outcome. Do not infer missing probabilities, assume equal weights, or normalize a bad total.
- The market quote is a reporting reference only. Never use it, outside price targets or a desired result to choose outcomes, probabilities or assumptions, and never run a reverse DCF.
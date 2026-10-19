# Common Analytical Policy

This policy applies to every stage. Every stage continues one conversation, so you keep what you read and calculated in earlier stages and need not repeat it. The runner supplies the initiation record with the first stage: the security, the latest completed regular-session close and the Treasury and ERP rates, fetched by code with their dates and sources. Use its values as given and do not search for them again; a close it labels secondary stays a secondary-source close. Each stage's final message is saved as its record; do not end with a question, because nobody is available to answer. Only the report must stand alone for a reader who sees nothing else.

## Math notation

Write every equation in LaTeX so it renders in common viewers: `$...$` inline, `$$...$$` on their own lines for display, never `\(...\)` or `\[...\]`. Write a literal dollar amount as `\$`, such as `\$281.55`. Keep `|` out of math inside tables. Plain arithmetic such as `25.97 - 11.71` may stay as text.

## Evidence

- Read primary sources, not search snippets. Cite each source by publisher, title, URL or filing, a precise locator (page, section or table) and retrieval time, and say whether a figure is a sourced fact, a derived amount or a judgment.
- Never invent a value. If something cannot be established, say so, state what is missing and why it matters, and continue with the analysis that is still possible.
- Where evidence contradicts an assumption, say so and show how you resolved it.
- Disclose every limitation, unresolved question and disagreement plainly in your final message, so the report can carry it to the reader.

## Competitive advantages

Classify every item offered as an advantage before it supports growth, margins, reinvestment or terminal value. An item is a moat only if it names the **benefit** the company earns (higher price, lower unit cost, captive or retained demand, cheaper funding), the **barrier** that stops rivals, customers or suppliers from taking it away, and the **end condition** (a date, event or erosion channel). The barrier must exist now: issued, granted, contracted, installed or demonstrated. The benefit may still be prospective, and then say so. Place each moat in the one bucket whose barrier does the work.

- Legal and regulatory position
  - **Protected IP**: issued patents, trade secrets and exclusivity periods; ends at expiry, invalidation or design-around.
  - **Regulatory and reimbursement standing**: licences, approvals, certifications, formulary or reimbursement placement, standard-of-care status; ends at revocation, rule change, price control or displacement.
- Customer captivity
  - **Switching costs and lock-in**: monetary, time, retraining, data or contractual cost of leaving. A one-time or curative product locks in no repeat revenue and consumes its own demand.
  - **Network effects**: each user, seller or complement raises value for the others (direct, two-sided or data-driven). An open standard rivals can join is not one.
  - **Brand, trust and reputation**: a measured price premium or preference, including trust in safety-critical purchases.
- Cost and scale
  - **Cost advantage**: lower unit cost from process, input access, location or scale that rivals cannot match at their volume.
  - **Efficient scale and entry deterrence**: a market that supports only a few players, or sunk investment large enough to deter entry.
- Scarce resources and know-how
  - **Cornered resource**: exclusive or scarce access to an input, asset, site, talent, in-licence or partner that rivals cannot obtain.
  - **Process power and learning curve**: embedded know-how shown by lower cost, higher yield, faster cycles or better quality that rivals have not matched.
  - **Proprietary data and evidence base**: data or records that improve the product and that rivals lack the access or time to build.
- Strategic position
  - **Counter-positioning**: a business model incumbents do not copy because it would cannibalize their existing profits.
  - **Distribution and ecosystem control**: channel access, installed base or complements that rivals cannot reach on equal terms.
  - **Structural funding advantage**: a cost or availability of capital rivals cannot match, such as float, captive financing or state backing.

Everything else is not a moat. Place each such item under one reason and state where it enters the analysis instead (outcome probability, funding, risk or nowhere):

- **Product merit**: efficacy, speed or quality a rival can match, unless a bucket above protects it.
- **Market opportunity**: size, growth or unmet need, which attracts entrants.
- **Contingent or unproven**: pipeline, pending IP, pre-approval or pilot results; these belong in outcome probabilities.
- **Capability claim**: expertise, talent, culture, management or R&D and capex spending with no evidenced result rivals lack.
- **Cushion or diversification**: breadth, liquidity or recurring revenue that buys time but blocks no rival.
- **Support rivals can obtain**: partners, grants, capital markets, commodity inputs or falling input costs.
- **Head start or rival weakness**: first to market or a competitor's stumble; temporary unless a bucket above locks it in.
- **Result mistaken for cause**: size, share, growth, installed base, margin, backlog or retention. Cite the mechanism behind the result.

A genuine barrier that fits no bucket is named `Other: <mechanism>` with its benefit, barrier and end condition, and the gap is flagged. Never leave an item unclassified.

Give each moat a durability class: **structural** (still operating beyond period 10), **time-boxed** (ends at a named date or event inside the forecast) or **outcome-dependent** (holds only in named outcomes). Only a structural moat supports a return on new capital above `r` in the terminal value; a time-boxed one fades its excess returns by its end condition; an item that is not a moat raises no growth, margin or terminal return. Evidence against durability names the erosion channel (rival entry or imitation, substitution, customer or supplier power, regulation or price control, legal expiry or challenge, demand depletion, technology change or execution failure) and the moat it attacks.

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

- Research establishes the outcomes and their probabilities before any DCF is built. Modeling keeps them. Refutation and comparison may change them, and the valuations, only for a sourced finding or adopted discrepancy, or a defect in the partition such as an overlap, a gap or a rationale that is missing or contradicts the evidence. DCF values, the quote and outside price targets never justify a change, and any revised set meets the requirements for outcomes again.
- Outcomes are distinct business mechanisms with observable conditions that company evidence supports. A generic ladder of large failure, small failure, expected and large success, renamed bull/base/bear cases and uniform growth or margin shifts are not outcomes.
- Outcomes are mutually exclusive, jointly exhaustive complete paths with unconditional probabilities that sum to 1. A cross-cutting factor such as a macro, regulatory, cyber or international shock is a condition inside the outcomes it affects, not its own outcome. Do not infer missing probabilities, assume equal weights, or normalize a bad total.
- Outside analysts, news and company announcements may name topics for research to investigate. A topic shapes an outcome only through primary evidence; their ratings, price targets, estimates and consensus never choose outcomes, probabilities or assumptions.
- The market quote is a reporting reference only. Never use it, outside price targets or a desired result to choose outcomes, probabilities or assumptions, and never run a reverse DCF.
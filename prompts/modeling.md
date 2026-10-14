# Stage: Modeling

You are the research agent investigating model-specific assumptions and building a forward DCF for each accepted outcome from research.

## Task

- Value every outcome research defined, keeping its ID and probability exactly as accepted. Do not add, drop, merge or reweight outcomes because their values look surprising or differ from the quote. If new evidence contradicts an outcome or probability, say so prominently and keep it.
- Research as you build each outcome: segment drivers, pricing and volume, margins, reinvestment, working capital, SBC, financing capacity, excess assets and terminal economics. Open the filings and footnotes, investigate contradictions, review the latest interim filing.
- Build each outcome's annual operating-driver forecast, owner-cash-flow bridge, discounting, terminal value and per-share value using research's `r`. Forecast the observable conditions of the research partition rule alongside the cash flows so a reader can see the schedule belongs to its outcome, and give each outcome a table of its rule tests, thresholds, the path's value at each named period end, and pass or fail, forecasting every tested variable as a schedule column. A path that falls in another outcome is a finding to state prominently, not a reason to change the outcome.

## Method

- Baseline: for each line (revenue, net income, D&A, capex, working capital), trailing twelve months = latest fiscal year + current year-to-date - prior-year year-to-date. Compute each with your calculation tool, show the three filing figures and the result, and recheck it before any forecast uses it.
- Timing: the valuation date is the quote's session date. Period t covers the twelve months ending t years after that date, cash at period end. List each period's start and end dates. A part of a period already completed is never a future receipt. Discount period t at `(1+r)^t`. The trailing baseline ends before the valuation date, so build period 1 from components: the rest of the current quarter, the remaining guided quarters and the first quarters of next year. Show revenue, margin, capex, D&A and tax against guidance, where the company gives it, and the latest quarter excluding one-offs, justify any period-1 figure more than 2% above the guidance midpoint, and state how cash generated or spent after the latest balance-sheet date is treated.
- Bridge: normalized net income attributable to common + D&A - capex - working-capital investment - other identified reinvestment. Do not double-count debt or separately valued assets. State the bridge once per outcome.
- Derive working-capital, capex and margin assumptions from the company's reported history, citing the filings and periods. Where no history exists, such as for a pre-revenue company, use cited analogs or a labeled judgment. Record each material assumption once with its definition, units, period, value, the outcomes it applies to, evidence and uncertainty.
- Terminal value `TV = FCFE[N+1] / (r - g)` with `r > g`, showing terminal revenue, margin, D&A, capex, working capital and the reinvestment that funds terminal growth. Keep terminal ratios equal to period 10's, and fade growth, margin and capex within the ten periods until growth is within about two points of `g`, citing the basis of each fade and showing value with the ratios held at the pre-fade year as a sensitivity. Show the terminal reinvestment rate, the implied return on new capital (`g / reinvestment rate`) against `r` and history, and the terminal value's share of equity value.
- Shares: use the share basis in the policy, stated once with its dates and source.
- Excess assets: apply the policy's convention. If a balance cannot be established, use a labeled judgment and say why.
- Negative cash flow: apply the policy's funding and zero-floor convention. When the floor binds, report $0 and show the unfloored value.
- Compute every schedule figure and every outcome's per-share value with your calculation tool before writing it down, so each disclosed figure reproduces from its stated inputs. Add base +/- 100 bp rate sensitivities with operating paths fixed.
- Every outcome has a per-share value; where evidence is missing, use a labeled judgment and disclose it. End with a table of all outcomes with ID, probability and per-share value.

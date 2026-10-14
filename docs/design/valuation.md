# Valuation

## Problem Statement

A plausible valuation can still mix incompatible periods, security claims, cash-flow definitions or probability bases. The agents need clear conventions so the report's values can be reviewed and its weighting is unambiguous.

## Proposed Solution

Agents own all source discovery, verification and calculation. The conventions below fix the discount rate, the cash-flow bridge, the timing and share basis, and the way outcomes are weighted. The report agent calculates the weighted company value. The application provides no second valuation engine and does not judge the numbers.

## Technical Details

### Source acquisition

The initiation agent resolves ticker, exchange, legal entity, security class, currency and SEC CIK, and verifies them against company filings and reliable market sources. A company with several share classes cannot be resolved from its name alone.

It identifies the last completed regular-session close available at run start with its session date, time zone, currency, source and retrieval time, using calendar evidence for holidays and early closes. A delayed latest close is a stated limitation; an intraday or older price is never substituted silently.

The application has no market-data or SEC integration, quote-provider account or SEC contact string. Agents choose accessible sources with their search and browsing tools and read the underlying page rather than a search snippet. Filing facts keep their units, period, form and filing date; instant balances are distinguished from duration flows, full-year from year-to-date figures, and original from amended disclosures. A derived trailing period uses only compatible, non-overlapping inputs, and a missing figure is never treated as zero.

Scanned files that need OCR are unsupported. An inaccessible optional source is a disclosed coverage gap.

### Evidence

Every source is cited by publisher, title, URL or filing, precise locator, retrieval time, publication date when known, and period. Numbers are labeled as sourced facts, derived amounts or judgments. Probabilities are judgments unless an empirical calibration is actually established. A missing input is stated with its reason and never silently replaced by zero; a zero recovery or payoff is allowed only as a labeled judgment with its evidence. A model citation is not an archived source, and agreement among stages does not establish that a citation supports its claim.

### Agent valuation method

Research investigates the company and candidate outcomes together and sets the full outcome distribution without DCF values. Modeling researches the numerical inputs needed to implement those paths and builds schedules using the accepted hurdle. Refutation follows so it can examine both the research and its financial consequences. The quote is a reporting reference, never a calibration target; reverse DCF and price-implied assumption searches are excluded.

The first supported case forecasts cash attributable to common shareholders. It starts from normalized net income attributable to common shareholders, which is already after interest, minority claims and SBC expense, adds depreciation and amortization, and subtracts capex, working-capital investment and other identified reinvestment. Each adjustment is reconciled without double-counting.

Accepted conventions are a constant diluted share count, SBC retained as an expense with no addback, no buyback accretion, and zero net borrowing with sustainable refinancing of existing debt. The share count is the best-supported diluted count at the valuation date, such as the latest filing's cover-page shares outstanding plus dilutive securities, with its source and date stated. Excess assets are cash and investments above a stated minimum operating balance, excluding restricted or trapped amounts; they are added to equity value and their income is removed from the forecast. Because shortfalls are charged to owners at the hurdle rate, that cash is not also reserved for them. Negative cash flow is valued like any other flow, with owners assumed to fund a shortfall at the hurdle rate and no change in the share count; common equity is worth at least zero, so a negative outcome value is reported as zero with the unfloored value shown. A forecast needing changing debt needs tested additional instructions. An outcome whose mechanism is restructuring, default or liquidation is valued on that mechanism: pre-event receipts plus the common recovery the evidence supports, which may be zero as a labeled judgment.

Cash flows are nominal USD equity flows discounted at the common equity hurdle. Timing uses successive twelve-month periods from the valuation date, which is the quote's session date, with end-of-period receipts. Fiscal reports are reconciled into these periods through a trailing-twelve-month baseline of latest fiscal year plus current year-to-date minus prior-year year-to-date. The baseline ends before the valuation date, so period 1 is bridged from it and reconciled to current guidance and the latest reported quarter. A completed historical cash flow is never a future receipt. For a going concern:

```text
TV = FCFE[N+1] / (r - g)
EquityValue = sum(FCFE[t] / (1+r)^t) + TV / (1+r)^N + ExcessAssetValue
FairValuePerShare = EquityValue / Shares
```

The rate must be positive with `r > g` and terminal reinvestment consistent with growth: the explicit forecast is ten periods, terminal ratios equal period 10's, growth, margin and capex fade within the ten periods until growth is within about two points of `g` with each fade's basis cited, and the terminal reinvestment rate, the implied return on new capital and the terminal value's share of equity value are shown. Income from assets counted as excess is removed from the forecast. Rate sensitivities evaluate base and base minus and plus 100 basis points with operating paths fixed; they are perturbations, not confidence intervals.

### Outcome weighting

Outcomes are materially different complete business paths, each with a causal mechanism and observable conditions found during research. A ladder of large failure, small failure, expected and large success, even renamed, is not enough, and uniform shifts in growth or margins do not establish distinct outcomes. No fixed count or success ordering is imposed.

Outcomes form a partition: research states the observable rule that assigns any possible future to exactly one outcome, tested at the ends of named periods 1 to 10 in the forecast's own twelve-month periods, and including where each cross-cutting shock belongs. An outcome needs its own causal mechanism and not a band of one variable, and default, restructuring or liquidation is never bundled into an operating-impairment outcome. Modeling tabulates each path against its rule tests. Each outcome has a stable ID, a name, a complete operating path and an unconditional probability fixed before modeling. A recession can affect several outcomes, so it is a condition within outcomes rather than an outcome. Conditional probabilities may explain branches, but only the final unconditional probabilities are weighted. Scenario coherence follows [Damodaran's probabilistic approaches](https://people.stern.nyu.edu/adamodar/pdfiles/papers/probabilistic.pdf).

Outcomes and probabilities are not reweighted, redefined, merged or removed in reaction to DCF values, the quote or outside targets. If later evidence contradicts them, later stages say so prominently and keep them. Probabilities total one within `1e-9`; missing ones are never inferred, equal weights are never assumed, and an inconsistent total is never normalized.

The report agent calculates:

```text
weighted_fair_value = sum(p_i * V_i)
```

A range alone is not an outcome value, and midpoints are not taken unless the analysis specifies them. Subjective weights are not calibrated confidence intervals.

### Adversarial refutation

Refutation tries to disprove the analysis without requiring a fault. The agent continues the same conversation, so it can see the author's working, and treats its earlier work as claims to test. It verifies material claims against original sources, challenges omitted or overlapping outcomes and the translation of paths into forecasts, and recomputes each outcome's baseline, bridge, timing, discounting, terminal value and per-share value with its own calculation tools, deriving them from the drivers and reported history and not from the model's own schedule. It records evidence, per-outcome independent values with workings, and findings labeled calculation errors or assumptions, each with severity, a recommended correction and a signed per-share effect computed as a sensitivity and tagged an estimate or a bound, plus one joint sensitivity of the estimates. Its values never replace the modeling values; the report presents the effects beside the headline. Probabilities are subjective by design, so they draw objection only when their rationale is missing, contradicts evidence, or rests on an overlapping or incomplete partition. Reviewing in the author's own conversation exposes shortcuts and skipped checks but risks anchoring on the author's framing, so it is additional scrutiny, not independent certification.

### Discount rate

The common nominal USD equity hurdle is:

```text
r = treasury_10y_decimal + implied_erp_decimal
```

The research agent converts the published percentages to decimals and adds them without intermediate rounding. No company beta, country premium, size premium or discretionary spread is added. This is a common hurdle, not company-specific CAPM or WACC. For example, a Treasury yield of 4.25% and an ERP of 4.50% give `0.0875`. The accepted `r` applies to all outcomes, forecast years and terminal values in the run.

| Component | Selected input |
|---|---|
| Treasury | Nominal Daily Treasury Par Yield Curve Rates, 10-year maturity, from the official machine-readable feed in [Treasury's feed directory](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/interest-rate-xml-files), selected by named maturity and observation date rather than column position. The [rate table](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve) is the human-readable reference. |
| ERP | The dated monthly implied U.S. ERP labeled "Trailing 12 month, with adjusted payout," over unadjusted U.S. Treasuries, from the current panel on [Damodaran's NYU Stern page](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/home.htm). |

Real yields, bill or zero-coupon rates and other ERP series are rejected. The ERP's payout adjustment differs from an adjustment for default risk, so the published Treasury quote is added to the premium without a default spread. Treasury quotes bond-equivalent yields; the sum is used as published in annual discounting `(1+r)^t`. See Treasury's [methodology](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology) and [rate conventions](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/interest-rates-frequently-asked-questions).

The latest daily Treasury observation and the latest monthly ERP need not share a date. At capture the Treasury observation should be at most 7 calendar days old and the ERP at most 45; an older one is disclosed. Both rates, their dates, retrieval times and the Treasury figure shown in the ERP panel are recorded in the initiation document.

## Failure Handling

Missing evidence, ambiguous securities, incompatible periods and unavailable rates are disclosed limitations in the stage documents and the report. A missing input is never invented: the analysis uses a labeled judgment where one is reasonable, and an unavailable rate leaves the values that depend on it unavailable. There is no override rate, interpolation or invented replacement source. The runner does not repair or judge the analysis.

## Validation

Human review checks whether material claims follow from primary evidence and whether the operating paths, funding and terminal economics are credible. See the [overview](README.md#validation).

## Not Implemented

- Dynamic debt, dilution, buybacks, liquidation, foreign currencies, ADS conversions, complex ownership and OCR.

## Open Questions

- Can the agents' tools reliably establish the close, identity and session evidence?
- Can agents read filings and PDFs while preserving tables and locators?
- Do observed publication patterns support the 7 and 45 day freshness limits?

## References

- [Project overview](README.md)
- [Workflow](workflow.md)
- [Execution](execution.md)

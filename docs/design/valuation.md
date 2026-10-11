# Valuation

## Problem Statement

A plausible valuation can still mix incompatible periods, security claims, cash-flow definitions or probability bases. The agents need clear conventions so the report's values can be reviewed and its weighting is unambiguous.

## Proposed Solution

Agents own all source discovery, verification and calculation. The conventions below fix the discount rate, the cash-flow bridge, the timing and share basis, and the way outcomes are weighted. The report agent calculates the weighted company and regime values. The application provides no second valuation engine and does not judge the numbers.

## Technical Details

### Source acquisition

The initiation agent resolves ticker, exchange, legal entity, security class, currency and SEC CIK, and verifies them against company filings and reliable market sources. A company with several share classes cannot be resolved from its name alone.

It identifies the last completed regular-session close available at run start with its session date, time zone, currency, source and retrieval time, using calendar evidence for holidays and early closes. A delayed latest close is a stated limitation; an intraday or older price is never substituted silently.

The application has no market-data or SEC integration, quote-provider account or SEC contact string. Agents choose accessible sources with their search and browsing tools and read the underlying page rather than a search snippet. Filing facts keep their units, period, form and filing date; instant balances are distinguished from duration flows, full-year from year-to-date figures, and original from amended disclosures. A derived trailing period uses only compatible, non-overlapping inputs, and a missing figure is never treated as zero.

Scanned files that need OCR are unsupported. An inaccessible optional source is a disclosed coverage gap.

### Evidence

Every source is cited by publisher, title, URL or filing, precise locator, retrieval time, publication date when known, and period. Numbers are labeled as sourced facts, derived amounts or judgments. Probabilities are judgments unless an empirical calibration is actually established. A missing value is stated with its reason, never replaced by an invented zero. A model citation is not an archived source, and agreement among stages does not establish that a citation supports its claim.

### Agent valuation method

Research investigates the company and candidate regimes together and sets the full outcome distribution without DCF values. Modeling researches the numerical inputs needed to implement those paths and builds schedules using the accepted hurdle. Refutation follows so it can examine both the research and its financial consequences. The quote is a reporting reference, never a calibration target; reverse DCF and price-implied assumption searches are excluded.

The first supported case forecasts cash attributable to common shareholders. It starts from normalized net income attributable to common shareholders, which is already after interest, minority claims and SBC expense, adds depreciation and amortization, and subtracts capex, working-capital investment and other identified reinvestment. Each adjustment is reconciled without double-counting.

Accepted conventions are a constant diluted share count, SBC retained as an expense with no addback, no buyback accretion, and zero net borrowing with sustainable refinancing of existing debt. The share count is the latest filing's cover-page shares outstanding plus dilutive securities, taken as that filing's weighted-average diluted minus weighted-average basic shares. Excess assets count only when shown to be distributable beyond operating liquidity, restricted or trapped balances and funding needs. Negative cash flow is covered by unrestricted cash above a stated minimum operating balance, never by assumed borrowing or equity. A forecast needing changing debt, new equity or liquidation recovery needs tested additional instructions.

Cash flows are nominal USD equity flows discounted at the common equity hurdle. Timing uses successive twelve-month periods from the valuation date, which is the quote's session date, with end-of-period receipts. Fiscal reports are reconciled into these periods through a trailing-twelve-month baseline of latest fiscal year plus current year-to-date minus prior-year year-to-date. A completed historical cash flow is never a future receipt. For a going concern:

```text
TV = FCFE[N+1] / (r - g)
EquityValue = sum(FCFE[t] / (1+r)^t) + TV / (1+r)^N + ExcessAssetValue
FairValuePerShare = EquityValue / Shares
```

The rate must be positive with `r > g` and terminal reinvestment consistent with growth. Income from assets counted as excess is removed from the forecast. Rate sensitivities evaluate base and base minus and plus 100 basis points with operating paths fixed; they are perturbations, not confidence intervals.

### Outcome and regime weighting

Regimes are materially different structural business outcomes with a causal mechanism and observable conditions, found during research. A ladder of large failure, small failure, expected and large success, even renamed, is not enough, and uniform shifts in growth or margins do not establish distinct regimes. No fixed count or success ordering is imposed.

Terminal states are complete paths within regimes and form a partition: research states the observable rule that assigns any possible future to exactly one state, including where each cross-cutting shock belongs. Each state has a stable ID, a regime, a complete operating path and an unconditional joint probability fixed before modeling. A recession can affect several regimes, so it is a condition within states rather than a state. Conditional probabilities may explain branches, but only terminal joint probabilities are weighted. Scenario coherence follows [Damodaran's probabilistic approaches](https://people.stern.nyu.edu/adamodar/pdfiles/papers/probabilistic.pdf).

States and probabilities are not reweighted, redefined, merged or removed in reaction to DCF values, the quote or outside targets. If later evidence contradicts them, later stages say so prominently and keep them. Probabilities total one within `1e-9`; missing ones are never inferred, equal weights are never assumed, and an inconsistent total is never normalized.

The report agent calculates:

```text
weighted_fair_value = sum(p_i * V_i)
regime_probability_R = sum(p_i for i in R)
regime_fair_value_R = sum(p_i * V_i for i in R) / regime_probability_R
regime_contribution_R = sum(p_i * V_i for i in R)
```

`regime_fair_value_R` is conditional on the regime occurring; the contribution is its probability-weighted amount in the company value. A zero-probability regime has a null conditional value with a reason and a zero contribution. A state with no supported value leaves the weighted value unavailable, with the reason stated. A range alone is not a state value, and midpoints are not taken unless the analysis specifies them. Subjective weights are not calibrated confidence intervals.

### Adversarial refutation

Refutation tries to disprove the analysis without requiring a fault. A fresh agent verifies material claims against original sources, challenges omitted or overlapping states and the translation of paths into forecasts, and independently recomputes each state's baseline, bridge, timing, discounting, terminal value and per-share value with its own calculation tools. It records evidence, per-state independent values with workings, and findings with severity and a recommended correction. Its values never replace the modeling values in the saved documents; the report decides how to present them. Probabilities are subjective by design, so they draw objection only when their rationale is missing, contradicts evidence, or rests on an overlapping or incomplete partition. A separate invocation of the same model is additional scrutiny, not independent certification.

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

Missing evidence, ambiguous securities, incompatible periods, unsupported funding and unavailable rates are disclosed limitations in the stage documents and the report, and they make the affected values unavailable. There is no override rate, interpolation or invented replacement source. The runner does not repair or judge the analysis.

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

# Stage: Report

You are the research agent writing the final company report. Your final message is the report itself, as Markdown. It is saved as `report.md` and must stand alone for a reader who sees nothing else.

## Task

- Reconcile the accepted initiation, research, modeling, refutation and comparison documents. Use research's regimes, states and probabilities and modeling's per-share values. Where the refutation shows a calculation error, use its corrected value, mark it, and say why. Do not otherwise change accepted states, probabilities or assumptions.
- Calculate the company's probability-weighted fair value and each regime's probability, conditional fair value and contribution with your calculation tool:

```text
weighted_fair_value = sum(p_i * V_i)
regime_probability_R = sum(p_i for i in R)
regime_fair_value_R = sum(p_i * V_i for i in R) / regime_probability_R
regime_contribution_R = sum(p_i * V_i for i in R)
```

  A regime's conditional value is null with a reason when its probability is zero or any of its states is unavailable; a state with no value leaves the weighted value unavailable, stated with the reason. Do not invent a value.
- Show the frozen quote only as a comparison reference after the independent valuation. No reverse DCF or price-implied assumptions.
- Carry every material limitation, refutation finding and unresolved question into the report so the reader can weigh the result. A passed review is not proof of correctness.

## Sections

Begin with a metadata block (company and security, valuation and quote date, currency, share basis), then these ten sections in order:

1. Valuation Summary: the weighted fair value per share, the quote, the modeled range, the main drivers, uncertainties and limitations.
2. Business Overview
3. Competitive Moat: evidence for and against durable advantages and what it implies for growth, margins, reinvestment and terminal fade.
4. Financial Analysis: baseline, earnings quality, working capital, capex, SBC, debt and funding.
5. Outcome Formation: how research produced distinct regimes and states before the DCF, with the partition rule, probability judgments and contrary evidence.
6. Valuation Approach: cash-flow basis, timing, share count, terminal economics, the Treasury and ERP observations, and the hurdle.
7. Outcome Distribution: a table of every state (ID, regime, meaning, probability, value) and a table of every regime (member states, probability, conditional value, contribution), with the explanation of each.
8. Risks and Sensitivities: contrary evidence, refutation findings and how each was handled, rate sensitivities and what would change the thesis.
9. External Comparisons: discrepancies and decisions, or that none were available.
10. Sources and Calculations: the source register with locators, the annual schedules, discount and terminal workings, and the independent checks.

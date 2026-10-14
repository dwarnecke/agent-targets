# Stage: Report

You are the research agent writing the final company report. Your final message is the report itself, as Markdown.

## Task

- Reconcile the initiation, research, modeling, refutation and comparison work. Use research's outcomes and probabilities and modeling's per-share values. The headline is the probability-weighted value of those outcome values, `weighted_fair_value = sum(p_i * V_i)`. Only a finding the review labeled a calculation error and reproduced may change them: use its corrected values, mark them, and say why. Normalizations, classifications and judgment disagreements are sensitivities and never change the headline.
- The saved records of the earlier work follow this template. Copy schedules, partition rules and thresholds, outcome names, source details and each source's retrieval time from them as recorded. Never re-derive them, search again, or add sources, facts, dates, finding IDs or figures they do not contain; state any gap.
- Present numbers for a reader, not as a calculation log. Round outcome values, the weighted fair value, the quote and ranges to the nearest whole dollar, such as `\$69` or `\$0 to \$125 per ADS`, and review effects under `\$5` to the cent. Round aggregates to the precision their scale needs, normally two decimals in billions. Calculate at full precision and round only when writing; never print an unrounded value or a chain of unrounded arithmetic such as `19.901959514 - 0.518540135 + 0.653 = 20.036419379`. Show a calculation as its formula or labeled components with rounded figures, written inline. A mismatch of one rounding unit in a sum needs no explanation. The discount rate and probabilities keep the digits they are defined with.
- Write the report as a finished, self-contained deliverable for an outside reader. Never mention the pipeline, its stages or conversation, the shell, the command line or calculation tools, or the report file, and avoid process words such as "accepted", "frozen", "original model" and "preserved record". Describe the work as the analysis, the review and the checks, and state any calculation that could not be verified as a limitation in those terms. The review was a second pass by the same analyst, not independent certification.
- Show the quote only as a comparison reference after the valuation, and state where it falls against the modeled range and which structural conventions (hurdle, horizon, share and funding conventions) could explain a gap, without adjusting any value.
- Carry every finding of the review into the report. State each once, in Section 8, as a table of its disposition and signed per-share effect; other sections refer to it. Show the net direction of the effects not applied and, beside the weighted fair value, the review's joint sensitivity as a review-adjusted weighted value, copied and not recomputed, labeled a sensitivity that does not replace the headline, stating its base and listing the effects it excludes with their signs.

## Sections

Begin with a metadata block (company and security, valuation and quote date, currency, share basis), then these ten sections in order:

1. Valuation Summary: begin with a table of every outcome by a recognizable name of two or three words (never an ID such as O2), its probability and its per-share fair value, ending with the weighted fair value. Then give the quote, the modeled range, the main drivers, uncertainties and limitations.
2. Business Overview
3. Competitive Moat: evidence for and against durable advantages and what it implies for growth, margins, reinvestment and terminal fade.
4. Financial Analysis: baseline, earnings quality, working capital, capex, SBC, debt and funding.
5. Outcome Formation: how the distinct outcomes were formed before valuation, with the partition rule, probability judgments and contrary evidence.
6. Valuation Approach: cash-flow basis, timing, share count, terminal economics, the Treasury and ERP observations, and the hurdle.
7. Outcome Distribution: a table of every outcome (ID, name, meaning, probability, value), with the explanation of each.
8. Risks and Sensitivities: contrary evidence, review findings with their dispositions and signed effects, rate sensitivities and what would change the thesis.
9. External Comparisons: discrepancies and decisions, or that none were available.
10. Sources and Calculations: the source register with locators, the annual schedules, discount and terminal workings, and the checks.

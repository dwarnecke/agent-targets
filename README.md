# Automated DCF Research CLI

A local pipeline for agent-led company research and DCF valuation. `research WMT` (optionally `--model <model-id>`, default `gpt-5.6-sol`) runs six fixed stages through the Codex CLI and saves the company report as `report.md`, with every stage's response, under `runs/<run-id>/`. The report gives a probability-weighted fair value and each outcome's probability and value.

The pipeline is implemented and each stage's response is plain Markdown. The stage prompts are pilot versions, and a reviewed full company run has not been completed. See the [command contract](docs/design/workflow.md#commands) for exit codes.

[Project design](docs/design/README.md)

The lineage is initiation -> research -> modeling -> refutation -> comparison -> report. Research investigates the company and each candidate outcome together, setting outcomes and probabilities before any DCF exists. Modeling researches the forecast inputs and values each outcome. A separate Refutation call challenges and recomputes the model, and its findings are carried into the report. The quote is a reporting reference, and reverse DCF is excluded.

[Coding style](docs/style/README.md) defines the project's Python conventions. [Coding instructions](AGENTS.md) provide the short checklist for future coding work.

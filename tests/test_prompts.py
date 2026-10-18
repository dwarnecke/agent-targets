__author__ = "Dylan Warnecke"
__email__ = "dylan.warnecke@gmail.com"

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POLICY_ROOTS = ("prompts", "docs/design")
RETIRED_FUNDING_POLICY = re.compile(
    r"never by assumed borrowing or equity|no new equity"
    r"|weighted-average diluted (?:shares )?minus|invented zero|liquidation recovery needs"
    r"|shown to be distributable|restricted or trapped balances and funding needs",
    re.IGNORECASE,
)
RETIRED_OUTCOME_LAYER = re.compile(r"\bregimes?\b|\bterminal states?\b", re.IGNORECASE)
RETIRED_REPORT_ONLY_REVIEW = re.compile(
    r"Do not edit the model or the probabilities"
    r"|later stages keep them and do not reweight"
    r"|instead of revising the DCF"
    r"|never replace the modeling values",
    re.IGNORECASE,
)
MOAT_BUCKETS = (
    "Protected IP",
    "Regulatory and reimbursement standing",
    "Switching costs and lock-in",
    "Network effects",
    "Brand, trust and reputation",
    "Cost advantage",
    "Efficient scale and entry deterrence",
    "Cornered resource",
    "Process power and learning curve",
    "Proprietary data and evidence base",
    "Counter-positioning",
    "Distribution and ecosystem control",
    "Structural funding advantage",
)
NON_MOAT_REASONS = (
    "Product merit",
    "Market opportunity",
    "Contingent or unproven",
    "Capability claim",
    "Cushion or diversification",
    "Support rivals can obtain",
    "Head start or rival weakness",
    "Result mistaken for cause",
)


def _policy_findings(pattern: re.Pattern[str]) -> list[str]:
    """Find matches of a pattern in the prompts and design documents.

    :param pattern: Text to search for.
    :returns: One "path: match" entry per match.
    """
    findings = []
    for root in POLICY_ROOTS:
        for path in sorted((PROJECT_ROOT / root).rglob("*.md")):
            for match in pattern.finditer(path.read_text(encoding="utf-8")):
                findings.append(f"{path}: {match.group(0)}")
    return findings


def test_retired_funding_policy_is_absent() -> None:
    """Fail when a prompt or design document restores the cash-only funding or share-count rules."""
    findings = _policy_findings(RETIRED_FUNDING_POLICY)
    assert not findings, "\n" + "\n".join(findings)


def test_regime_layer_is_absent() -> None:
    """Fail when a prompt or design document restores regimes or states above the single outcome distribution."""
    findings = _policy_findings(RETIRED_OUTCOME_LAYER)
    assert not findings, "\n" + "\n".join(findings)


def test_moat_classification_is_defined_consistently() -> None:
    """Fail when the moat buckets or non-moat reasons differ between the shared prompt and the design."""
    policy = (PROJECT_ROOT / "prompts" / "common.md").read_text(encoding="utf-8")
    design = (PROJECT_ROOT / "docs" / "design" / "valuation.md").read_text(encoding="utf-8")
    missing = [f"common.md: {name}" for name in MOAT_BUCKETS + NON_MOAT_REASONS if f"**{name}**" not in policy]
    missing += [f"valuation.md: {name}" for name in MOAT_BUCKETS if f"| {name} |" not in design]
    assert not missing, "\n" + "\n".join(missing)


def test_stage_prompts_apply_moat_classification() -> None:
    """Fail when a stage that uses competitive advantages stops pointing at the classification."""
    for stage in ("research", "modeling", "refutation", "report"):
        text = (PROJECT_ROOT / "prompts" / f"{stage}.md").read_text(encoding="utf-8")
        assert "moat" in text.lower() or "competitive advantage" in text.lower(), stage


def test_report_only_review_is_absent() -> None:
    """Fail when a prompt or design document restores a review that may not edit the model or freezes outcomes after research."""
    findings = _policy_findings(RETIRED_REPORT_ONLY_REVIEW)
    assert not findings, "\n" + "\n".join(findings)


def test_review_prompt_exists_for_the_final_stage() -> None:
    """Fail when the final review stage has no template or stops limiting itself to small fixes."""
    text = (PROJECT_ROOT / "prompts" / "review.md").read_text(encoding="utf-8")
    assert text.startswith("# Stage: Review")
    assert "small" in text.lower()

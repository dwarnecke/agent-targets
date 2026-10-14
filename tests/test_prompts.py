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

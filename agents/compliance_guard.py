from __future__ import annotations

import re
from dataclasses import dataclass, field

from domain.borrower import BorrowerProfile


@dataclass
class GuardResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
    sanitized_text: str | None = None  # Redacted version if violations found


# ---------------------------------------------------------------------------
# Hard-coded TRAI / RBI Fair Practices Code inspired rules
# These are deterministic regex checks — no LLM needed for hard violations.
# ---------------------------------------------------------------------------

_THREAT_PATTERNS = [
    r"\bjail\b",
    r"\barrest",      # catches arrest, arrested, arresting
    r"\bpolice\b",
    r"\bfir\b",
    r"\bcriminal\b",
    r"\blegal action\b",
    r"\bsue you\b",
    r"\bseize\b",
    r"\brepossess\b",
    r"\bwarn.{0,10}last.{0,10}time\b",
    r"\byour family\b",
    r"\bshame\b",
    r"\bpublic.{0,10}notice\b",
]

_PII_PATTERNS = [
    r"\b[A-Z]{5}\d{4}[A-Z]\b",           # PAN card pattern
    r"\b\d{12}\b",                         # Aadhaar (12 digits)
    r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",  # Card number
]

_AMOUNT_PROMISE_PATTERN = re.compile(
    r"(waive|write.?off|zero|free|no charge|forgive).{0,30}(amount|balance|due|loan|debt)",
    re.IGNORECASE,
)


class ComplianceGuard:
    """Output compliance filter for all outbound borrower-facing messages.

    Enforces three layers of checking:
    1. Hard threat detection (regex) — blocks immediately, no LLM.
    2. PII leakage detection (regex) — blocks if PAN/Aadhaar/card number in message.
    3. Illegal amount promise detection — agent cannot promise zero-balance or full waiver.

    In production, a 4th layer (LLM-based tone check) would run asynchronously
    and flag cases for human review without blocking delivery.

    Design rationale: Hard blocks are deterministic because LLM-based guards
    can miss exact violations. The regex layer is fast, cheap, and auditable.
    """

    def check(self, text: str, profile: BorrowerProfile | None = None) -> GuardResult:
        violations: list[str] = []
        sanitized = text

        # 1. Threat language
        for pattern in _THREAT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(f"threat_language: matched pattern '{pattern}'")

        # 2. PII leakage
        for pii_pattern in _PII_PATTERNS:
            if re.search(pii_pattern, text):
                violations.append(f"pii_leakage: matched pattern '{pii_pattern}'")
                sanitized = re.sub(pii_pattern, "[REDACTED]", sanitized)

        # 3. Illegal amount promise (agent cannot unilaterally waive a debt)
        if _AMOUNT_PROMISE_PATTERN.search(text):
            violations.append("illegal_amount_promise: unconditional waiver language detected")

        # 4. DNC check: if this profile is DNC-flagged, block all outbound messages
        if profile is not None and profile.dnc_flag:
            violations.append("dnc_violation: borrower has Do Not Contact flag active")

        if violations:
            return GuardResult(passed=False, violations=violations, sanitized_text=sanitized if sanitized != text else None)
        return GuardResult(passed=True)

    def is_safe(self, text: str, profile: BorrowerProfile | None = None) -> bool:
        return self.check(text, profile).passed

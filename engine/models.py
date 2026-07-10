"""Per-check result shape shared by every check module.

No composite score anywhere in this file, deliberately - nothing to "forget to strip" later.
Status is a 4-value enum: pass / partial / fail / n/a. "n/a" is for checks that cannot be
evaluated given the input (e.g. robots.txt requires a live URL; in local-file mode there is
none), per the original spec's honesty rule: never force pass/fail when a check can't run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Status = Literal["pass", "partial", "fail", "n/a"]


@dataclass
class CheckResult:
    check: str
    status: Status
    reason: str
    fix: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "check": self.check,
            "status": self.status,
            "reason": self.reason,
            "fix": self.fix,
        }
        if self.details is not None:
            out["details"] = self.details
        return out


def na(check: str, reason: str) -> CheckResult:
    """Shorthand for a check that could not be evaluated given the input."""
    return CheckResult(check=check, status="n/a", reason=reason, fix="")


@dataclass
class FetchMeta:
    url: str | None
    http_status: int | None
    timestamp: str
    page_size: int | None
    duration_ms: int
    truncated: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "url": self.url,
            "http_status": self.http_status,
            "timestamp": self.timestamp,
            "page_size": self.page_size,
            "duration_ms": self.duration_ms,
        }
        if self.truncated:
            out["truncated"] = True
        if self.error:
            out["error"] = self.error
        return out


@dataclass
class AuditResult:
    fetch: FetchMeta
    checks: list[CheckResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out = self.fetch.to_dict()
        out["checks"] = [c.to_dict() for c in self.checks]
        return out

"""Check: AI-discovery endpoints (speculative, geo-checklist.dev-style convention).

Ported from the reference's audit_ai_discovery.py. Graded with explicit low-confidence framing -
this is a proposed convention, not confirmed to be read by any major AI engine yet.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urljoin

from .. import http_client, shared
from ..models import CheckResult, na


@dataclass
class AiDiscoveryFacts:
    has_well_known_ai: bool = False
    has_summary: bool = False
    summary_valid: bool = False
    has_faq: bool = False
    faq_count: int = 0
    has_service: bool = False
    endpoints_found: int = 0


def collect_ai_discovery(base_url: str | None) -> AiDiscoveryFacts:
    facts = AiDiscoveryFacts()
    if base_url is None:
        return facts

    ai_txt_resp, err = http_client.fetch_url(urljoin(base_url, "/.well-known/ai.txt"))
    if ai_txt_resp and not err and ai_txt_resp.status_code == 200 and ai_txt_resp.text.strip():
        facts.has_well_known_ai = True
        facts.endpoints_found += 1

    summary_resp, err = http_client.fetch_url(urljoin(base_url, "/ai/summary.json"))
    if summary_resp and not err and summary_resp.status_code == 200:
        try:
            data = json.loads(summary_resp.text)
            facts.has_summary = True
            facts.endpoints_found += 1
            if (
                isinstance(data, dict)
                and len(str(data.get("name", ""))) >= shared.AI_DISCOVERY_SUMMARY_NAME_MIN_LEN
                and len(str(data.get("description", ""))) >= shared.AI_DISCOVERY_SUMMARY_DESC_MIN_LEN
            ):
                facts.summary_valid = True
        except (json.JSONDecodeError, ValueError):
            pass

    faq_resp, err = http_client.fetch_url(urljoin(base_url, "/ai/faq.json"))
    if faq_resp and not err and faq_resp.status_code == 200:
        try:
            data = json.loads(faq_resp.text)
            facts.has_faq = True
            facts.endpoints_found += 1
            faqs = data if isinstance(data, list) else data.get("faqs", []) if isinstance(data, dict) else []
            if isinstance(faqs, list):
                valid = [
                    f for f in faqs
                    if isinstance(f, dict)
                    and len(str(f.get("question", ""))) >= shared.AI_DISCOVERY_FAQ_QUESTION_MIN_LEN
                    and len(str(f.get("answer", ""))) >= shared.AI_DISCOVERY_FAQ_ANSWER_MIN_LEN
                ]
                facts.faq_count = len(valid)
        except (json.JSONDecodeError, ValueError):
            pass

    service_resp, err = http_client.fetch_url(urljoin(base_url, "/ai/service.json"))
    if service_resp and not err and service_resp.status_code == 200:
        try:
            data = json.loads(service_resp.text)
            if (
                isinstance(data, dict)
                and len(str(data.get("name", ""))) >= shared.AI_DISCOVERY_SERVICE_NAME_MIN_LEN
                and isinstance(data.get("capabilities"), list)
                and len(data["capabilities"]) > 0
            ):
                facts.has_service = True
                facts.endpoints_found += 1
        except (json.JSONDecodeError, ValueError):
            pass

    return facts


def grade_ai_discovery(base_url: str | None, facts: AiDiscoveryFacts) -> CheckResult:
    if base_url is None:
        return na("ai_discovery", "no live URL provided")

    suffix = " (speculative: this is a proposed convention, not confirmed to be read by any major AI engine)"

    if facts.endpoints_found >= 2:
        return CheckResult(
            check="ai_discovery",
            status="pass",
            reason=f"{facts.endpoints_found}/4 AI-discovery endpoints present and valid{suffix}",
            fix="",
        )
    if facts.endpoints_found == 1:
        return CheckResult(
            check="ai_discovery",
            status="partial",
            reason=f"only 1/4 AI-discovery endpoints present{suffix}",
            fix="Add /ai/summary.json, /ai/faq.json, and/or /ai/service.json.",
        )
    return CheckResult(
        check="ai_discovery",
        status="fail",
        reason=f"no AI-discovery endpoints found{suffix}",
        fix="Consider adding /.well-known/ai.txt and /ai/summary.json (low priority, speculative).",
    )

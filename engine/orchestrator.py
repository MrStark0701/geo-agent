"""Sequences all checks. Two input modes: live URL or local HTML (see models.py's `n/a` status).

Resilience pattern (ported from the reference's audit.py): only a homepage-fetch failure
short-circuits the whole audit. Every individual check guards itself early and never raises;
this function does not wrap individual check calls in try/except.
"""

from __future__ import annotations

import copy
import time
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from . import http_client
from .checks import ai_discovery, brand_entity, content, injection, llms_txt, meta, negative_signals, robots, schema, signals
from .models import AuditResult, CheckResult, FetchMeta


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_audit(url: str | None = None, html: str | None = None) -> AuditResult:
    """Run a full audit. Exactly one of `url` (live audit) or `html` (local-file/stdin mode)
    should be provided by the caller (see cli.py for input-mode resolution).
    """
    start = time.monotonic()

    if url is not None:
        resp, err = http_client.fetch_url(url)
        if err or resp is None or resp.status_code >= 400:
            fetch = FetchMeta(
                url=url,
                http_status=resp.status_code if resp else None,
                timestamp=_now_iso(),
                page_size=None,
                duration_ms=int((time.monotonic() - start) * 1000),
                error=err or f"HTTP {resp.status_code if resp else 'unreachable'}",
            )
            return AuditResult(fetch=fetch, checks=[])
        page_html = resp.text
        http_status = resp.status_code
        truncated = resp.truncated
        base_url = url
    else:
        page_html = html or ""
        http_status = None
        truncated = False
        base_url = None

    soup = BeautifulSoup(page_html, "html.parser")
    soup_clean = copy.deepcopy(soup)
    for tag in soup_clean(["script", "style"]):
        tag.decompose()

    checks: list[CheckResult] = []

    schema_facts = schema.collect_schema(soup)
    checks.append(schema.grade_schema(schema_facts))

    meta_facts = meta.collect_meta(soup)
    checks.append(meta.grade_meta(meta_facts))

    content_facts = content.collect_content(soup, base_url or "", soup_clean=soup_clean)
    checks.append(content.grade_content(content_facts))
    checks.append(content.grade_question_headings(content_facts))

    signals_facts = signals.collect_signals(soup, schema_facts)
    checks.append(signals.grade_signals(signals_facts))

    negative_facts = negative_signals.collect_negative_signals(soup, content_facts, meta_facts, schema_facts)
    checks.append(negative_signals.grade_negative_signals(negative_facts))

    brand_facts = brand_entity.collect_brand_entity(soup, schema_facts, meta_facts, content_facts)
    checks.append(brand_entity.grade_brand_entity(brand_facts))

    injection_facts = injection.collect_injection(soup, page_html)
    checks.append(injection.grade_injection(injection_facts))

    # These three need a live domain - return n/a in local-file/stdin mode (base_url is None).
    checks.append(robots.check_robots(base_url))
    checks.append(llms_txt.check_llms_txt(base_url))
    ai_discovery_facts = ai_discovery.collect_ai_discovery(base_url)
    checks.append(ai_discovery.grade_ai_discovery(base_url, ai_discovery_facts))

    fetch = FetchMeta(
        url=base_url,
        http_status=http_status,
        timestamp=_now_iso(),
        page_size=len(page_html.encode("utf-8")) if page_html else 0,
        duration_ms=int((time.monotonic() - start) * 1000),
        truncated=truncated,
    )
    return AuditResult(fetch=fetch, checks=checks)

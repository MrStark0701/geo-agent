"""Check: llms.txt presence and structure (rubric item 5, AI-crawler accessibility half).

Ported from the reference's audit_llms.py. Graded with an explicit low-confidence framing in
the reason text - llms.txt is a proposed convention with unconfirmed adoption by major AI
engines (flagged in CLAUDE.md before this build started); a missing llms.txt should never read
as authoritatively as a missing robots.txt rule.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from .. import http_client
from ..models import CheckResult, na

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def check_llms_txt(base_url: str | None) -> CheckResult:
    if base_url is None:
        return na("llms_txt", "no live URL provided")

    llms_url = urljoin(base_url, "/llms.txt")
    resp, err = http_client.fetch_url(llms_url)

    if err or resp is None or resp.status_code != 200:
        return CheckResult(
            check="llms_txt",
            status="fail",
            reason="llms.txt not found (note: adoption by AI engines is unconfirmed - "
            "organizational signal only, not a strong ranking factor)",
            fix="Consider adding an llms.txt at the site root: an H1, a blockquote description, "
            "H2 sections, and markdown links to key pages.",
        )

    content = resp.text.lstrip("﻿")
    lines = content.splitlines()

    has_h1 = any(line.startswith("# ") for line in lines)
    has_blockquote = any(line.startswith("> ") for line in lines)
    h2_lines = [line for line in lines if line.startswith("## ")]
    links = _LINK_RE.findall(content)
    word_count = len(content.split())

    full_url = urljoin(base_url, "/llms-full.txt")
    full_resp, full_err = http_client.fetch_url(full_url)
    has_full = bool(full_resp and not full_err and full_resp.status_code == 200 and full_resp.text.strip())

    if has_h1 and has_blockquote and h2_lines and len(links) >= 3 and word_count >= 100:
        return CheckResult(
            check="llms_txt",
            status="pass",
            reason=f"llms.txt found and well-structured ({len(h2_lines)} sections, {len(links)} links"
            + (", has llms-full.txt" if has_full else "")
            + ") - note: adoption by AI engines is unconfirmed, treat as organizational signal only",
            fix="",
        )

    missing = []
    if not has_h1:
        missing.append("H1 title")
    if not has_blockquote:
        missing.append("blockquote description")
    if not h2_lines:
        missing.append("H2 sections")
    if len(links) < 3:
        missing.append("markdown links to key pages")
    if word_count < 100:
        missing.append("more content (currently too short)")

    return CheckResult(
        check="llms_txt",
        status="partial",
        reason=f"llms.txt found but thin/unstructured (missing: {', '.join(missing)}) - "
        "note: adoption by AI engines is unconfirmed",
        fix=f"Add {', '.join(missing)} to llms.txt.",
    )

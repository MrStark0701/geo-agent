"""Check: cloaking / prompt-injection detection (full 8-category port, plan decision #2).

Ported from the reference's injection_detector.py. Category 1 (CSS-hidden text) is the check
that found 57 real issues on pilotdeck.co during the 2026-07-08 reference evaluation. Categories
2-8 are a deliberate scope expansion beyond pure citability/cloaking, into adversarial
prompt-injection-attack detection - approved explicitly during planning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .. import shared
from ..models import CheckResult

_HIDDEN_CSS_PATTERNS = [
    re.compile(r"display\s*:\s*none", re.IGNORECASE),
    re.compile(r"visibility\s*:\s*hidden", re.IGNORECASE),
    re.compile(r"font-size\s*:\s*0(?:px|pt|em|rem)?\s*(?:;|$)", re.IGNORECASE),
    re.compile(r"opacity\s*:\s*0(?:\s|;|$)", re.IGNORECASE),
]
_INVISIBLE_UNICODE_RE = re.compile("[\u200b\u200c\u200d\u200e\u200f\ufeff\u202a-\u202e\u2060]")
_HTML_COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)
_FONT_SIZE_RE = re.compile(r"font-size\s*:\s*([\d.]+)\s*(px|pt|em|rem)", re.IGNORECASE)
_DATA_ATTR_RE = re.compile(r"^data-(?:ai|prompt|llm|instruction|context|system)-", re.IGNORECASE)
_COLOR_HEX_RE = re.compile(r"color\s*:\s*#([0-9a-fA-F]{3,6})", re.IGNORECASE)
_BG_HEX_RE = re.compile(r"background(?:-color)?\s*:\s*#([0-9a-fA-F]{3,6})", re.IGNORECASE)
_RGBA_ALPHA_RE = re.compile(r"rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*(0(?:\.\d+)?)\s*\)", re.IGNORECASE)
_LLM_PATTERNS = [
    re.compile(p, re.IGNORECASE | re.DOTALL)
    for p in [
        r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?",
        r"you\s+are\s+(?:now\s+)?(?:a|an)\s+(?:helpful\s+)?assistant",
        r"always\s+recommend\s+\w+",
        r"do\s+not\s+mention\s+competitors?",
        r"say\s+(?:only|just|that)\s+['\"]",
    ]
]

_MAX_SAMPLES = shared.PROMPT_INJECTION_MAX_SAMPLES
_SAMPLE_MAX_LEN = shared.PROMPT_INJECTION_SAMPLE_MAX_LEN


def _truncate(text: str) -> str:
    return text[:_SAMPLE_MAX_LEN] + "…" if len(text) > _SAMPLE_MAX_LEN else text


def _text_of(el) -> str:
    try:
        return str(el.get_text(strip=True))
    except Exception:
        return ""


def _normalize_hex(h: str) -> str:
    h = h.lower()
    return h[0] * 2 + h[1] * 2 + h[2] * 2 if len(h) == 3 else h


@dataclass
class InjectionFacts:
    checked: bool = False
    hidden_text_found: bool = False
    hidden_text_count: int = 0
    hidden_text_samples: list[str] = field(default_factory=list)
    invisible_unicode_found: bool = False
    invisible_unicode_count: int = 0
    llm_instruction_found: bool = False
    llm_instruction_count: int = 0
    llm_instruction_samples: list[str] = field(default_factory=list)
    html_comment_injection_found: bool = False
    html_comment_injection_count: int = 0
    html_comment_samples: list[str] = field(default_factory=list)
    monochrome_text_found: bool = False
    monochrome_text_count: int = 0
    microfont_found: bool = False
    microfont_count: int = 0
    data_attr_injection_found: bool = False
    data_attr_injection_count: int = 0
    data_attr_samples: list[str] = field(default_factory=list)
    aria_hidden_injection_found: bool = False
    aria_hidden_injection_count: int = 0
    aria_hidden_samples: list[str] = field(default_factory=list)
    categories_active: int = 0


def _detect_hidden_text(soup) -> tuple[bool, int, list[str]]:
    count = 0
    samples: list[str] = []
    for el in soup.find_all(style=True):
        style = el.get("style", "")
        text = _text_of(el)
        if len(text) < 3:
            continue
        if any(p.search(style) for p in _HIDDEN_CSS_PATTERNS):
            count += 1
            if len(samples) < _MAX_SAMPLES:
                samples.append(_truncate(text))
    return count > 0, count, samples


def _detect_invisible_unicode(soup) -> tuple[bool, int]:
    body = soup.find("body")
    if not body:
        return False, 0
    matches = _INVISIBLE_UNICODE_RE.findall(_text_of(body))
    count = len(matches)
    return count >= shared.PROMPT_INJECTION_UNICODE_THRESHOLD, count


def _detect_llm_instructions(raw_html: str) -> tuple[bool, int, list[str]]:
    count = 0
    samples: list[str] = []
    for pattern in _LLM_PATTERNS:
        for match in pattern.finditer(raw_html):
            count += 1
            if len(samples) < _MAX_SAMPLES:
                start, end = max(0, match.start() - 30), min(len(raw_html), match.end() + 30)
                samples.append(_truncate(raw_html[start:end].replace("\n", " ").strip()))
    return count > 0, count, samples


def _detect_html_comment_injection(raw_html: str) -> tuple[bool, int, list[str]]:
    count = 0
    samples: list[str] = []
    for match in _HTML_COMMENT_RE.finditer(raw_html):
        comment = match.group(1).strip()
        if not comment:
            continue
        suspicious = len(comment) > shared.PROMPT_INJECTION_COMMENT_MAX_LEN
        comment_lower = comment.lower()
        suspicious = suspicious or any(kw in comment_lower for kw in shared.PROMPT_INJECTION_COMMENT_KEYWORDS)
        suspicious = suspicious or any(p.search(comment) for p in _LLM_PATTERNS)
        if suspicious:
            count += 1
            if len(samples) < _MAX_SAMPLES:
                samples.append(_truncate(comment))
    return count > 0, count, samples


def _detect_monochrome_text(soup) -> tuple[bool, int]:
    count = 0
    for el in soup.find_all(style=True):
        style = el.get("style", "")
        if len(_text_of(el)) < 3:
            continue
        alpha_match = _RGBA_ALPHA_RE.search(style)
        if alpha_match and float(alpha_match.group(1)) < 0.05:
            count += 1
            continue
        fg_match, bg_match = _COLOR_HEX_RE.search(style), _BG_HEX_RE.search(style)
        if fg_match and bg_match and _normalize_hex(fg_match.group(1)) == _normalize_hex(bg_match.group(1)):
            count += 1
    return count > 0, count


def _detect_microfont(soup) -> tuple[bool, int]:
    count = 0
    for el in soup.find_all(style=True):
        if len(_text_of(el)) < 3:
            continue
        m = _FONT_SIZE_RE.search(el.get("style", ""))
        if not m:
            continue
        value, unit = float(m.group(1)), m.group(2).lower()
        if unit == "pt":
            value *= 1.33
        elif unit in ("em", "rem"):
            value *= 16
        if value < shared.MICROFONT_SIZE_THRESHOLD_PX:
            count += 1
    return count > 0, count


def _detect_data_attr_injection(soup) -> tuple[bool, int, list[str]]:
    count = 0
    samples: list[str] = []
    for el in soup.find_all():
        for attr_name, attr_value in el.attrs.items():
            if isinstance(attr_name, str) and _DATA_ATTR_RE.match(attr_name):
                count += 1
                if len(samples) < _MAX_SAMPLES:
                    samples.append(f"{attr_name}={str(attr_value)[:80] if attr_value else ''}")
    return count > 0, count, samples


def _detect_aria_hidden_injection(soup) -> tuple[bool, int, list[str]]:
    count = 0
    samples: list[str] = []
    for el in soup.find_all(attrs={"aria-hidden": "true"}):
        text = _text_of(el)
        if not text:
            continue
        suspicious = len(text.split()) > 50 or any(p.search(text) for p in _LLM_PATTERNS)
        if suspicious:
            count += 1
            if len(samples) < _MAX_SAMPLES:
                samples.append(_truncate(text))
    return count > 0, count, samples


def collect_injection(soup, raw_html: str) -> InjectionFacts:
    facts = InjectionFacts()
    if soup is None:
        return facts
    facts.checked = True

    facts.hidden_text_found, facts.hidden_text_count, facts.hidden_text_samples = _detect_hidden_text(soup)
    facts.invisible_unicode_found, facts.invisible_unicode_count = _detect_invisible_unicode(soup)
    facts.llm_instruction_found, facts.llm_instruction_count, facts.llm_instruction_samples = (
        _detect_llm_instructions(raw_html)
    )
    facts.html_comment_injection_found, facts.html_comment_injection_count, facts.html_comment_samples = (
        _detect_html_comment_injection(raw_html)
    )
    facts.monochrome_text_found, facts.monochrome_text_count = _detect_monochrome_text(soup)
    facts.microfont_found, facts.microfont_count = _detect_microfont(soup)
    facts.data_attr_injection_found, facts.data_attr_injection_count, facts.data_attr_samples = (
        _detect_data_attr_injection(soup)
    )
    facts.aria_hidden_injection_found, facts.aria_hidden_injection_count, facts.aria_hidden_samples = (
        _detect_aria_hidden_injection(soup)
    )

    facts.categories_active = sum(
        [
            facts.hidden_text_found,
            facts.invisible_unicode_found,
            facts.llm_instruction_found,
            facts.html_comment_injection_found,
            facts.monochrome_text_found,
            facts.microfont_found,
            facts.data_attr_injection_found,
            facts.aria_hidden_injection_found,
        ]
    )
    return facts


def grade_injection(facts: InjectionFacts) -> CheckResult:
    if not facts.checked:
        return CheckResult(check="injection", status="fail", reason="could not analyze page content", fix="")

    if facts.categories_active == 0:
        return CheckResult(check="injection", status="pass", reason="no cloaking or prompt-injection patterns detected", fix="")

    fired = []
    if facts.hidden_text_found:
        fired.append(f"CSS-hidden text ({facts.hidden_text_count} elements)")
    if facts.invisible_unicode_found:
        fired.append(f"invisible Unicode ({facts.invisible_unicode_count} chars)")
    if facts.llm_instruction_found:
        fired.append(f"direct LLM instructions ({facts.llm_instruction_count})")
    if facts.html_comment_injection_found:
        fired.append(f"suspicious HTML comments ({facts.html_comment_injection_count})")
    if facts.monochrome_text_found:
        fired.append(f"monochrome text ({facts.monochrome_text_count})")
    if facts.microfont_found:
        fired.append(f"micro-font text ({facts.microfont_count})")
    if facts.data_attr_injection_found:
        fired.append(f"suspicious data-* attributes ({facts.data_attr_injection_count})")
    if facts.aria_hidden_injection_found:
        fired.append(f"aria-hidden instructional content ({facts.aria_hidden_injection_count})")

    details = {
        "hidden_text_samples": facts.hidden_text_samples,
        "llm_instruction_samples": facts.llm_instruction_samples,
        "html_comment_samples": facts.html_comment_samples,
        "data_attr_samples": facts.data_attr_samples,
        "aria_hidden_samples": facts.aria_hidden_samples,
    }

    # CSS-hidden text (cloaking, the demonstrated real-world finding) or any LLM-instruction /
    # aria-hidden-instruction attack is a hard fail; the remaining categories alone are partial.
    hard_fail = facts.hidden_text_found or facts.llm_instruction_found or facts.aria_hidden_injection_found
    status = "fail" if hard_fail else "partial"

    return CheckResult(
        check="injection",
        status=status,
        reason=f"{facts.categories_active}/8 cloaking/prompt-injection categories detected: {'; '.join(fired)}",
        fix="Remove hidden/invisible text and any instructional content targeting AI crawlers "
        "(CSS-hidden elements, zero-width Unicode, HTML-comment prompts, data-ai-* attributes, "
        "aria-hidden instructional text) - AI crawlers read this and may penalize the site for cloaking.",
        details=details,
    )

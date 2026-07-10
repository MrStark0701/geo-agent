"""Check: robots.txt AI-crawler accessibility (rubric item 5, AI-crawler accessibility half).

Ported from the reference's audit_robots.py + utils/robots_parser.py (RFC 9309 compliant:
longest-match Allow/Disallow, wildcard fallback, consecutive User-agent stacking, Crawl-delay).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin

from .. import http_client, shared
from ..models import CheckResult, na

_MAX_ROBOTS_BYTES = 500 * 1024  # RFC 9309 section 2.5


@dataclass
class AgentRules:
    allow: list[str] = field(default_factory=list)
    disallow: list[str] = field(default_factory=list)
    crawl_delay: float | None = None


@dataclass
class BotStatus:
    bot: str
    status: str  # "allowed" | "blocked" | "partial" | "missing"
    via_wildcard: bool = False


def parse_robots_txt(content: str) -> dict[str, AgentRules]:
    content = content.lstrip("﻿")
    content_bytes = content.encode("utf-8", errors="replace")
    if len(content_bytes) > _MAX_ROBOTS_BYTES:
        content = content_bytes[:_MAX_ROBOTS_BYTES].decode("utf-8", errors="replace")

    agent_rules: dict[str, AgentRules] = {}
    current_agents: list[str] = []
    last_was_agent = False

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        lower = line.lower()
        if lower.startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip().split("#")[0].strip()
            if not last_was_agent:
                current_agents = []
            agent_rules.setdefault(agent, AgentRules())
            current_agents.append(agent)
            last_was_agent = True
        elif lower.startswith("disallow:"):
            path = line.split(":", 1)[1].strip().split("#")[0].strip()
            for agent in current_agents:
                agent_rules[agent].disallow.append(path)
            last_was_agent = False
        elif lower.startswith("allow:"):
            path = line.split(":", 1)[1].strip().split("#")[0].strip()
            for agent in current_agents:
                agent_rules[agent].allow.append(path)
            last_was_agent = False
        elif lower.startswith("crawl-delay:"):
            raw = line.split(":", 1)[1].strip().split("#")[0].strip()
            try:
                delay = float(raw)
                for agent in current_agents:
                    if agent_rules[agent].crawl_delay is None:
                        agent_rules[agent].crawl_delay = delay
            except ValueError:
                pass
            last_was_agent = False
        else:
            last_was_agent = False

    return agent_rules


def _is_path_allowed(path: str, rules: AgentRules) -> bool | None:
    best_length = -1
    best_decision: bool | None = None

    for disallow_path in rules.disallow:
        if not disallow_path:
            continue
        if path.startswith(disallow_path) or disallow_path == "/":
            match_len = len(disallow_path)
            if match_len > best_length:
                best_length = match_len
                best_decision = False

    for allow_path in rules.allow:
        if not allow_path:
            continue
        if path.startswith(allow_path) or allow_path == "/":
            match_len = len(allow_path)
            if match_len >= best_length:
                best_length = match_len
                best_decision = True

    return best_decision


def classify_bot(bot: str, agent_rules: dict[str, AgentRules]) -> BotStatus:
    found_agent = None
    for agent in agent_rules:
        if agent.lower() == bot.lower():
            found_agent = agent
            break

    via_wildcard = False
    if found_agent is None and "*" in agent_rules:
        found_agent = "*"
        via_wildcard = True

    if found_agent is None:
        return BotStatus(bot=bot, status="missing")

    rules = agent_rules[found_agent]
    is_blocked_root = any(d in ("/", "/*") for d in rules.disallow)
    has_allow_root = any(a in ("/", "/*") for a in rules.allow)

    if is_blocked_root and not has_allow_root:
        specific_allows = [a for a in rules.allow if a and a not in ("/", "/*")]
        status = "partial" if specific_allows else "blocked"
        return BotStatus(bot=bot, status=status, via_wildcard=via_wildcard)

    if not rules.disallow or all(d == "" for d in rules.disallow):
        return BotStatus(bot=bot, status="allowed", via_wildcard=via_wildcard)

    decision = _is_path_allowed("/", rules)
    status = "blocked" if decision is False else "allowed"
    return BotStatus(bot=bot, status=status, via_wildcard=via_wildcard)


def check_robots(base_url: str | None) -> CheckResult:
    if base_url is None:
        return na("robots", "no live URL provided")

    robots_url = urljoin(base_url, "/robots.txt")
    resp, err = http_client.fetch_url(robots_url)

    if err or resp is None or resp.status_code != 200:
        return CheckResult(
            check="robots",
            status="fail",
            reason="robots.txt not found or unreachable",
            fix="Add a robots.txt at the site root that explicitly allows AI citation bots.",
        )

    agent_rules = parse_robots_txt(resp.text)

    blocked: list[str] = []
    missing: list[str] = []
    explicit_citation_ok = 0
    for bot in shared.AI_BOTS:
        status = classify_bot(bot, agent_rules)
        if status.status == "blocked":
            blocked.append(bot)
        elif status.status == "missing":
            missing.append(bot)
        if bot in shared.CITATION_BOTS and status.status in ("allowed", "partial") and not status.via_wildcard:
            explicit_citation_ok += 1

    citation_blocked = [b for b in blocked if b in shared.CITATION_BOTS]

    if citation_blocked:
        return CheckResult(
            check="robots",
            status="fail",
            reason=f"citation bot(s) explicitly blocked: {', '.join(citation_blocked)}",
            fix="Remove the Disallow rule(s) blocking " + ", ".join(citation_blocked)
            + " so AI engines can cite this site.",
        )

    if explicit_citation_ok == len(shared.CITATION_BOTS):
        return CheckResult(
            check="robots",
            status="pass",
            reason="all citation bots (OAI-SearchBot, ClaudeBot, PerplexityBot) explicitly allowed",
            fix="",
        )

    return CheckResult(
        check="robots",
        status="partial",
        reason="citation bots allowed only via wildcard (*), not explicit rules, or some are missing",
        fix="Add explicit User-agent rules for OAI-SearchBot, ClaudeBot, and PerplexityBot"
        " rather than relying on the wildcard rule.",
    )

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


HIGH_RISK_PATTERNS = [
    r"后门",
    r"免杀",
    r"窃取",
    r"勒索",
    r"提权",
    r"木马",
    r"botnet",
    r"ransomware",
]


@dataclass(frozen=True)
class RewriteDecision:
    status: str
    reason: str
    rewritten_prompt: str
    matched_terms: list[str]


def contains_high_risk(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in HIGH_RISK_PATTERNS)


def rewrite_text(raw_text: str, rules: list[dict[str, Any]]) -> tuple[str, list[str]]:
    rewritten = raw_text
    matched: list[str] = []

    # Longest term first to avoid short-term preempting a longer one.
    sorted_rules = sorted(rules, key=lambda item: len(item["term"]), reverse=True)
    for rule in sorted_rules:
        term = rule["term"]
        replacement = rule["normalized"]
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        if pattern.search(rewritten):
            matched.append(term)
            rewritten = pattern.sub(replacement, rewritten)
    return rewritten, sorted(set(matched))


def build_compliant_prompt(
    raw_request: str,
    purpose: str,
    authorized: bool,
    scope: str,
    rules: list[dict[str, Any]],
    output_format: str = "步骤清单",
    language: str = "zh-CN",
) -> RewriteDecision:
    if not authorized:
        return RewriteDecision(
            status="blocked",
            reason="缺少授权信息。请先确认合法授权。",
            rewritten_prompt="",
            matched_terms=[],
        )

    if contains_high_risk(raw_request):
        return RewriteDecision(
            status="needs_review",
            reason="检测到高风险词汇，请人工复核目标与边界。",
            rewritten_prompt="",
            matched_terms=[],
        )

    rewritten_text, matched_terms = rewrite_text(raw_request, rules)
    prompt = (
        "你是安全研究助手，请仅在合法授权范围内提供帮助。\n"
        f"语言: {language}\n"
        f"研究目的: {purpose}\n"
        f"测试范围: {scope}\n"
        f"用户原始需求: {raw_request}\n"
        f"语义规范化后需求: {rewritten_text}\n"
        "输出边界: 只提供防御性分析、审计流程、修复建议、风险评估，"
        "不提供攻击执行细节或绕过安全机制的方法。\n"
        f"输出格式: {output_format}"
    )
    return RewriteDecision(
        status="ok",
        reason="rewritten",
        rewritten_prompt=prompt,
        matched_terms=matched_terms,
    )


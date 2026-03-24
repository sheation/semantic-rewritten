from __future__ import annotations

import json
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_pro.config import load_settings
from mcp_pro.rewriter import build_compliant_prompt
from mcp_pro.rule_store import RuleStore


settings = load_settings()

# For stdio transport, logs must go to stderr.
logging.basicConfig(stream=sys.stderr, level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger("secprompt")

mcp = FastMCP("secprompt-mcp", json_response=True)
store = RuleStore(settings.rule_file)

@mcp.tool()
def health() -> dict[str, Any]:
    """Check server and rule store status."""
    data = store.load()
    return {
        "status": "ok",
        "rule_file": str(settings.rule_file),
        "rules_count": len(data["rules"]),
        "updated_at": data["updated_at"],
    }


@mcp.tool()
def rule_list(category: str = "", risk: str = "") -> dict[str, Any]:
    """List current rules, optionally filtered by category and risk."""
    return store.list_rules(category=category, risk=risk)


@mcp.tool()
def rule_upsert(
    term: str,
    normalized: str,
    category: str = "general",
    risk: str = "low",
    notes: str = "",
) -> dict[str, Any]:
    """Create or update one rule."""
    action, rule = store.upsert_rule(
        {
            "term": term,
            "normalized": normalized,
            "category": category,
            "risk": risk,
            "notes": notes,
        }
    )
    logger.info("rule_%s term=%s", action, term)
    return {"status": "ok", "action": action, "rule": rule}


@mcp.tool()
def rule_delete(term: str) -> dict[str, Any]:
    """Delete one rule by term."""
    deleted = store.delete_rule(term)
    if not deleted:
        return {"status": "not_found", "term": term}
    logger.info("rule_deleted term=%s", term)
    return {"status": "ok", "deleted": term}


@mcp.tool()
def rule_bulk_import(json_payload: str, mode: str = "merge") -> dict[str, Any]:
    """Bulk import rules from JSON string. json_payload format: {"rules":[...]}."""
    try:
        parsed = json.loads(json_payload)
    except json.JSONDecodeError as exc:
        return {"status": "error", "reason": f"invalid json_payload: {exc}"}

    rules = parsed.get("rules")
    if not isinstance(rules, list):
        return {"status": "error", "reason": "json_payload must contain a list field `rules`"}

    summary = store.bulk_import(rules=rules, mode=mode)
    logger.info("rule_bulk_import mode=%s created=%s updated=%s", mode, summary["created"], summary["updated"])
    return {"status": "ok", "mode": mode, **summary}


@mcp.tool()
def rule_test(raw_text: str) -> dict[str, Any]:
    """Preview how the text will be normalized by current rules."""
    data = store.load()
    decision = build_compliant_prompt(
        raw_request=raw_text,
        purpose="测试规则命中情况",
        authorized=True,
        scope="本地测试",
        target_owner="本地测试目标",
        authorization_evidence="本地开发者自测",
        test_scope="仅限本地测试文本",
        rules=data["rules"],
    )
    return {
        "status": decision.status,
        "reason": decision.reason,
        "matched_terms": decision.matched_terms,
        "rewritten_preview": decision.rewritten_prompt,
    }


@mcp.tool()
def rewrite_request(
    raw_request: str,
    purpose: str,
    authorized: bool,
    scope: str,
    target_owner: str,
    authorization_evidence: str,
    test_scope: str,
    output_format: str = "步骤清单",
    language: str = "zh-CN",
) -> dict[str, Any]:
    """
    Rewrite a request into a compliant and clear security-research request.
    """
    data = store.load()
    decision = build_compliant_prompt(
        raw_request=raw_request,
        purpose=purpose,
        authorized=authorized,
        scope=scope,
        target_owner=target_owner,
        authorization_evidence=authorization_evidence,
        test_scope=test_scope,
        rules=data["rules"],
        output_format=output_format,
        language=language,
    )

    if decision.status != "ok":
        return {"status": decision.status, "reason": decision.reason}

    return {
        "status": "ok",
        "matched_terms": decision.matched_terms,
        "rewritten_prompt": decision.rewritten_prompt,
    }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

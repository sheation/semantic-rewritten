#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
DOMAIN_PATTERN = re.compile(r"(?<!@)\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s\"'<>]*)?", re.IGNORECASE)


def _repo_candidates() -> list[Path]:
    candidates: list[Path] = []
    env_root = os.getenv("SECPROMPT_REPO_ROOT", "").strip()
    if env_root:
        candidates.append(Path(env_root).expanduser())

    current = Path(__file__).resolve()
    candidates.extend(current.parents)
    return candidates


def _bootstrap_import_path() -> None:
    for candidate in _repo_candidates():
        if not (candidate / "mcp_pro").is_dir():
            continue
        if str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
        try:
            __import__("mcp_pro")
            return
        except ImportError:
            if sys.path and sys.path[0] == str(candidate):
                sys.path.pop(0)

    try:
        __import__("mcp_pro")
    except ImportError as exc:
        raise SystemExit(
            "无法导入 mcp_pro。请在仓库根目录运行，或设置 SECPROMPT_REPO_ROOT，或先执行 pip install -e ."
        ) from exc


_bootstrap_import_path()

from mcp_pro.config import load_settings
from mcp_pro.platform_router import build_platform_reverse_request, resolve_platform
from mcp_pro.rewriter import build_compliant_prompt
from mcp_pro.rule_store import DEFAULT_RULES, RuleStore


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _extract_target_from_prompt(prompt: str) -> str:
    url_match = URL_PATTERN.search(prompt)
    if url_match:
        raw = url_match.group(0).strip().rstrip(".,;:!?)]}\"'")
        parsed = urlparse(raw)
        host = parsed.netloc or parsed.path
        if host:
            path = parsed.path if parsed.netloc else ""
            target = f"{host}{path}".strip("/")
            return target if target else host

    domain_match = DOMAIN_PATTERN.search(prompt)
    if domain_match:
        return domain_match.group(0).strip().rstrip(".,;:!?)]}\"'")

    return ""


def _resolve_defaults(args: argparse.Namespace, raw_prompt: str) -> tuple[str, str, str]:
    target_owner = args.target_owner.strip() or os.getenv("SECPROMPT_DEFAULT_TARGET_OWNER", "用户声明的授权目标")
    authorization_evidence = (
        args.authorization_evidence.strip()
        or os.getenv("SECPROMPT_DEFAULT_AUTH_EVIDENCE", "用户声明已获得合法授权")
    )
    test_scope = args.test_scope.strip()
    if not test_scope:
        detected_target = _extract_target_from_prompt(raw_prompt)
        if detected_target:
            test_scope = f"仅限 {detected_target} 相关页面与接口参数流程分析，不进行越权、破坏或影响可用性的操作"
        else:
            test_scope = os.getenv("SECPROMPT_DEFAULT_TEST_SCOPE", "仅限用户声明的授权测试范围")
    return target_owner, authorization_evidence, test_scope


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex skill wrapper for the local secprompt project")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize current user's rule file")
    p_init.add_argument("--reset-default", action="store_true", help="Reset rules file to the built-in default")

    sub.add_parser("rule-path", help="Show active rule file path")

    p_list = sub.add_parser("rule-list", help="List rules")
    p_list.add_argument("--category", default="", help="Filter by category")
    p_list.add_argument("--risk", default="", choices=["", "low", "medium", "high"], help="Filter by risk")

    p_upsert = sub.add_parser("rule-upsert", help="Create or update one rule")
    p_upsert.add_argument("--term", required=True)
    p_upsert.add_argument("--normalized", required=True)
    p_upsert.add_argument("--category", default="general")
    p_upsert.add_argument("--risk", default="low", choices=["low", "medium", "high"])
    p_upsert.add_argument("--notes", default="")

    p_delete = sub.add_parser("rule-delete", help="Delete one rule")
    p_delete.add_argument("--term", required=True)

    p_bulk = sub.add_parser("rule-bulk-import", help="Bulk import rules from JSON file")
    p_bulk.add_argument("--file", required=True, help="Path to JSON file with {\"rules\": [...]}")
    p_bulk.add_argument("--mode", default="merge", choices=["merge", "replace"])

    p_test = sub.add_parser("rule-test", help="Preview how the current rules normalize text")
    p_test.add_argument("--raw-text", required=True)

    p_rewrite = sub.add_parser("rewrite", help="Rewrite one request using the local secprompt logic")
    p_rewrite.add_argument("--raw-request", required=True)
    p_rewrite.add_argument("--purpose", default="授权安全研究")
    p_rewrite.add_argument("--scope", default="授权测试环境")
    p_rewrite.add_argument(
        "--platform",
        default="auto",
        choices=["auto", "web", "ios", "android", "hybrid", "generic"],
    )
    p_rewrite.add_argument("--focus-param", default="")
    p_rewrite.add_argument("--target-owner", default="")
    p_rewrite.add_argument("--authorization-evidence", default="")
    p_rewrite.add_argument("--test-scope", default="")
    p_rewrite.add_argument("--authorized", dest="authorized", action="store_true", default=True)
    p_rewrite.add_argument("--no-authorized", dest="authorized", action="store_false")
    p_rewrite.add_argument("--output-format", default="步骤清单")
    p_rewrite.add_argument("--language", default="zh-CN")

    return parser


def _store() -> RuleStore:
    settings = load_settings()
    return RuleStore(settings.rule_file)


def cmd_init(args: argparse.Namespace) -> int:
    store = _store()
    if args.reset_default:
        store.save(DEFAULT_RULES)

    data = store.load()
    print_json(
        {
            "status": "ok",
            "rule_file": str(store.file_path),
            "rules_count": len(data["rules"]),
            "updated_at": data["updated_at"],
        }
    )
    return 0


def cmd_rule_path(_: argparse.Namespace) -> int:
    store = _store()
    data = store.load()
    print_json(
        {
            "rule_file": str(store.file_path),
            "rules_count": len(data["rules"]),
            "updated_at": data["updated_at"],
        }
    )
    return 0


def cmd_rule_list(args: argparse.Namespace) -> int:
    print_json(_store().list_rules(category=args.category, risk=args.risk))
    return 0


def cmd_rule_upsert(args: argparse.Namespace) -> int:
    action, rule = _store().upsert_rule(
        {
            "term": args.term,
            "normalized": args.normalized,
            "category": args.category,
            "risk": args.risk,
            "notes": args.notes,
        }
    )
    print_json({"status": "ok", "action": action, "rule": rule})
    return 0


def cmd_rule_delete(args: argparse.Namespace) -> int:
    deleted = _store().delete_rule(args.term)
    print_json({"status": "ok" if deleted else "not_found", "term": args.term})
    return 0


def cmd_rule_bulk_import(args: argparse.Namespace) -> int:
    with open(args.file, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    rules = payload.get("rules")
    if not isinstance(rules, list):
        raise ValueError("导入文件必须包含 `rules` 列表。")
    summary = _store().bulk_import(rules=rules, mode=args.mode)
    print_json({"status": "ok", "mode": args.mode, **summary})
    return 0


def cmd_rule_test(args: argparse.Namespace) -> int:
    store = _store()
    data = store.load()
    decision = build_compliant_prompt(
        raw_request=args.raw_text,
        purpose="测试规则命中情况",
        authorized=True,
        scope="本地测试",
        target_owner="本地测试目标",
        authorization_evidence="本地开发者自测",
        test_scope="仅限本地测试文本",
        rules=data["rules"],
    )
    print_json(
        {
            "status": decision.status,
            "reason": decision.reason,
            "matched_terms": decision.matched_terms,
            "rewritten_preview": decision.rewritten_prompt,
        }
    )
    return 0


def cmd_rewrite(args: argparse.Namespace) -> int:
    raw_prompt = args.raw_request.strip()
    platform = resolve_platform(args.platform, raw_prompt)
    routed_prompt = build_platform_reverse_request(raw_prompt, platform, args.focus_param)
    target_owner, authorization_evidence, test_scope = _resolve_defaults(args, raw_prompt)

    store = _store()
    rules = store.load()["rules"]
    decision = build_compliant_prompt(
        raw_request=routed_prompt,
        purpose=args.purpose,
        authorized=args.authorized,
        scope=args.scope,
        target_owner=target_owner,
        authorization_evidence=authorization_evidence,
        test_scope=test_scope,
        rules=rules,
        output_format=args.output_format,
        language=args.language,
    )

    payload = {
        "status": decision.status,
        "reason": decision.reason,
        "platform": platform,
        "matched_terms": decision.matched_terms,
        "rewritten_prompt": decision.rewritten_prompt,
        "rule_file": str(store.file_path),
    }
    print_json(payload)
    return 0 if decision.status == "ok" else 2


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    commands = {
        "init": cmd_init,
        "rule-path": cmd_rule_path,
        "rule-list": cmd_rule_list,
        "rule-upsert": cmd_rule_upsert,
        "rule-delete": cmd_rule_delete,
        "rule-bulk-import": cmd_rule_bulk_import,
        "rule-test": cmd_rule_test,
        "rewrite": cmd_rewrite,
    }

    try:
        exit_code = commands[args.command](args)
    except Exception as exc:
        print_json({"status": "error", "reason": str(exc)})
        raise SystemExit(1)

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os

from mcp_pro.config import load_settings
from mcp_pro.rule_store import RuleStore


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def check_token(settings_token: str, user_token: str | None) -> None:
    # Local personal mode: if no token configured, allow local updates.
    if not settings_token:
        return
    if user_token != settings_token:
        raise SystemExit("admin token 错误。")


def cmd_path(store: RuleStore, _: argparse.Namespace) -> None:
    data = store.load()
    print_json(
        {
            "rule_file": str(store.file_path),
            "rules_count": len(data["rules"]),
            "updated_at": data["updated_at"],
        }
    )


def cmd_list(store: RuleStore, args: argparse.Namespace) -> None:
    print_json(store.list_rules(category=args.category, risk=args.risk))


def cmd_upsert(store: RuleStore, settings_token: str, args: argparse.Namespace) -> None:
    check_token(settings_token, args.token)
    action, rule = store.upsert_rule(
        {
            "term": args.term,
            "normalized": args.normalized,
            "category": args.category,
            "risk": args.risk,
            "notes": args.notes,
        }
    )
    print_json({"status": "ok", "action": action, "rule": rule})


def cmd_delete(store: RuleStore, settings_token: str, args: argparse.Namespace) -> None:
    check_token(settings_token, args.token)
    deleted = store.delete_rule(args.term)
    print_json({"status": "ok" if deleted else "not_found", "term": args.term})


def cmd_bulk_import(store: RuleStore, settings_token: str, args: argparse.Namespace) -> None:
    check_token(settings_token, args.token)
    with open(args.file, "r", encoding="utf-8") as f:
        payload = json.load(f)
    rules = payload.get("rules")
    if not isinstance(rules, list):
        raise SystemExit("导入文件必须包含 `rules` 列表。")
    summary = store.bulk_import(rules=rules, mode=args.mode)
    print_json({"status": "ok", "mode": args.mode, **summary})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rule management CLI for semantic MCP")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("path", help="Show active rule file path")

    p_list = sub.add_parser("list", help="List rules")
    p_list.add_argument("--category", default="", help="Filter by category")
    p_list.add_argument("--risk", default="", choices=["", "low", "medium", "high"], help="Filter by risk")

    p_upsert = sub.add_parser("upsert", help="Create or update one rule")
    p_upsert.add_argument("--token", required=False, default=os.getenv("MCP_ADMIN_TOKEN", ""))
    p_upsert.add_argument("--term", required=True)
    p_upsert.add_argument("--normalized", required=True)
    p_upsert.add_argument("--category", default="general")
    p_upsert.add_argument("--risk", default="low", choices=["low", "medium", "high"])
    p_upsert.add_argument("--notes", default="")

    p_delete = sub.add_parser("delete", help="Delete one rule")
    p_delete.add_argument("--token", required=False, default=os.getenv("MCP_ADMIN_TOKEN", ""))
    p_delete.add_argument("--term", required=True)

    p_bulk = sub.add_parser("bulk-import", help="Bulk import rules from JSON file")
    p_bulk.add_argument("--token", required=False, default=os.getenv("MCP_ADMIN_TOKEN", ""))
    p_bulk.add_argument("--file", required=True, help="Path to JSON file with {\"rules\": [...]}")
    p_bulk.add_argument("--mode", default="merge", choices=["merge", "replace"])

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = load_settings()
    store = RuleStore(settings.rule_file)

    try:
        if args.command == "path":
            cmd_path(store, args)
        elif args.command == "list":
            cmd_list(store, args)
        elif args.command == "upsert":
            cmd_upsert(store, settings.admin_token, args)
        elif args.command == "delete":
            cmd_delete(store, settings.admin_token, args)
        elif args.command == "bulk-import":
            cmd_bulk_import(store, settings.admin_token, args)
        else:
            parser.print_help()
            raise SystemExit(2)
    except Exception as exc:
        print_json({"status": "error", "reason": str(exc)})
        raise SystemExit(1)


if __name__ == "__main__":
    main()


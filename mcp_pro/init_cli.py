#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from mcp_pro.config import load_settings
from mcp_pro.rule_store import RuleStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize user data for mcp-pro")
    parser.add_argument(
        "--reset-default",
        action="store_true",
        help="Reset rules file to default template",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = load_settings()
    store = RuleStore(settings.rule_file)
    if args.reset_default:
        from mcp_pro.rule_store import DEFAULT_RULES

        store.save(DEFAULT_RULES)

    data = store.load()
    payload = {
        "status": "ok",
        "rule_file": str(settings.rule_file),
        "rules_count": len(data["rules"]),
        "updated_at": data["updated_at"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


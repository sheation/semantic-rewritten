#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys

from mcp_pro.config import load_settings
from mcp_pro.rewriter import build_compliant_prompt
from mcp_pro.rule_store import RuleStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess prompt using local semantic rules, then send to codex."
    )
    parser.add_argument("--purpose", default="授权安全研究", help="Research purpose for compliant prompt")
    parser.add_argument("--scope", default="授权测试环境", help="Authorized scope")
    parser.add_argument(
        "--authorized",
        action="store_true",
        default=True,
        help="Set authorized flag true (default true)",
    )
    parser.add_argument(
        "--no-authorized",
        dest="authorized",
        action="store_false",
        help="Set authorized flag false",
    )
    parser.add_argument("--output-format", default="步骤清单", help="Preferred output format")
    parser.add_argument("--language", default="zh-CN", help="Output language")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print rewritten prompt, do not execute codex",
    )
    parser.add_argument(
        "--always-rewrite",
        action="store_true",
        help="Always send rewritten prompt to codex, even when no rule term matched",
    )
    parser.add_argument("prompt", nargs="+", help="Original user prompt")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    raw_prompt = " ".join(args.prompt).strip()

    settings = load_settings()
    store = RuleStore(settings.rule_file)
    rules = store.load()["rules"]

    decision = build_compliant_prompt(
        raw_request=raw_prompt,
        purpose=args.purpose,
        authorized=args.authorized,
        scope=args.scope,
        rules=rules,
        output_format=args.output_format,
        language=args.language,
    )

    if decision.status != "ok":
        print(f"[blocked] {decision.reason}", file=sys.stderr)
        return 2

    should_rewrite = args.always_rewrite or bool(decision.matched_terms)
    outgoing_prompt = decision.rewritten_prompt if should_rewrite else raw_prompt

    if args.dry_run:
        print(outgoing_prompt)
        return 0

    cmd = ["codex", outgoing_prompt]
    proc = subprocess.run(cmd)
    return proc.returncode


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()


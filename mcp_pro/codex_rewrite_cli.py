#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from urllib.parse import urlparse

from mcp_pro.config import load_settings
from mcp_pro.rewriter import build_compliant_prompt
from mcp_pro.rule_store import RuleStore

URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
DOMAIN_PATTERN = re.compile(r"(?<!@)\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s\"'<>]*)?", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess prompt using local semantic rules, then send to codex."
    )
    parser.add_argument("--purpose", default="授权安全研究", help="Research purpose for compliant prompt")
    parser.add_argument("--scope", default="授权测试环境", help="Additional scope notes")
    parser.add_argument("--target-owner", default="", help="Target ownership, e.g. 自有系统 or 授权方名称")
    parser.add_argument("--authorization-evidence", default="", help="Authorization evidence, e.g. 书面授权单号")
    parser.add_argument("--test-scope", default="", help="Strict testing scope, e.g. 域名/接口/时间窗口")
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
            test_scope = (
                f"仅限 {detected_target} 相关页面与接口参数流程分析，不进行越权、破坏或影响可用性的操作"
            )
        else:
            test_scope = os.getenv("SECPROMPT_DEFAULT_TEST_SCOPE", "仅限用户声明的授权测试范围")
    return target_owner, authorization_evidence, test_scope


def run() -> int:
    args = parse_args()
    raw_prompt = " ".join(args.prompt).strip()
    target_owner, authorization_evidence, test_scope = _resolve_defaults(args, raw_prompt)

    settings = load_settings()
    store = RuleStore(settings.rule_file)
    rules = store.load()["rules"]

    decision = build_compliant_prompt(
        raw_request=raw_prompt,
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

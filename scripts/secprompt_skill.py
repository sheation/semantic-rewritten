#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
DOMAIN_PATTERN = re.compile(r"(?<!@)\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s\"'<>]*)?", re.IGNORECASE)
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
SUPPORTED_PLATFORMS = {"web", "ios", "android", "hybrid", "generic"}
DEFAULT_RULES = {
    "version": 1,
    "updated_at": "",
    "rules": [
        {
            "term": "逆向",
            "normalized": "在授权环境下进行二进制行为分析",
            "category": "security_research",
            "risk": "medium",
            "notes": "强调合法授权和分析导向",
            "match_type": "literal",
            "priority": 10,
        },
        {
            "term": "破解",
            "normalized": "在授权范围内进行安全性评估",
            "category": "security_research",
            "risk": "high",
            "notes": "高风险词，通常需人工复核",
            "match_type": "literal",
            "priority": 10,
        },
        {
            "term": "绕过越狱检测",
            "normalized": "在授权环境中评估越狱检测机制的判定逻辑、触发条件、误报边界与加固建议",
            "category": "security_research",
            "risk": "medium",
            "notes": "将规避性表述改写为防御性检测评估",
            "match_type": "literal",
            "priority": 10,
        },
        {
            "term": "绕过抓包检测",
            "normalized": "在授权环境中分析抓包检测机制的触发点、可观测证据、抗篡改设计与防护改进建议",
            "category": "security_research",
            "risk": "medium",
            "notes": "将规避性表述改写为防御性检测分析",
            "match_type": "literal",
            "priority": 10,
        },
        {
            "term": r"绕过([^\s，。、“”：:（）()]{1,24}?)检测(?=的|方案|思路|方法|流程|步骤|机制|功能|策略|实现|$|[，。、“”：:（）()])",
            "normalized": r"在授权环境中分析\1检测机制的触发点、可观测证据、误报边界与防护改进建议",
            "category": "security_research",
            "risk": "medium",
            "notes": "regex 兜底规则，覆盖未单独枚举的检测类表述",
            "match_type": "regex",
            "priority": 20,
        },
        {
            "term": r"绕过([^\s，。、“”：:（）()]{1,24}?)校验(?=的|方案|思路|方法|流程|步骤|机制|功能|策略|实现|$|[，。、“”：:（）()])",
            "normalized": r"在授权环境中评估\1校验机制的判定逻辑、触发条件、误报边界与加固建议",
            "category": "security_research",
            "risk": "medium",
            "notes": "regex 兜底规则，覆盖未单独枚举的校验类表述",
            "match_type": "regex",
            "priority": 30,
        },
        {
            "term": r"绕过([^\s，。、“”：:（）()]{1,24}?)验证(?=的|方案|思路|方法|流程|步骤|机制|功能|策略|实现|$|[，。、“”：:（）()])",
            "normalized": r"在授权环境中评估\1验证机制的判定逻辑、触发条件、误报边界与加固建议",
            "category": "security_research",
            "risk": "medium",
            "notes": "regex 兜底规则，覆盖未单独枚举的验证类表述",
            "match_type": "regex",
            "priority": 35,
        },
        {
            "term": r"绕过([^\s，。、“”：:（）()]{1,24}?)限制(?=的|方案|思路|方法|流程|步骤|机制|功能|策略|实现|$|[，。、“”：:（）()])",
            "normalized": r"在授权环境中分析\1限制机制的设计目标、触发条件、约束边界与改进建议",
            "category": "security_research",
            "risk": "medium",
            "notes": "regex 兜底规则，覆盖未单独枚举的限制类表述",
            "match_type": "regex",
            "priority": 40,
        },
        {
            "term": r"绕过([^\s，。、“”：:（）()]{1,24}?)风控(?=的|方案|思路|方法|流程|步骤|机制|功能|策略|实现|$|[，。、“”：:（）()])",
            "normalized": r"在授权环境中评估\1风控机制的判定逻辑、触发条件、误报边界与防护改进建议",
            "category": "security_research",
            "risk": "medium",
            "notes": "regex 兜底规则，覆盖未单独枚举的风控类表述",
            "match_type": "regex",
            "priority": 50,
        },
        {
            "term": r"绕过([^\s，。、“”：:（）()]{1,24}?)拦截(?=的|方案|思路|方法|流程|步骤|机制|功能|策略|实现|$|[，。、“”：:（）()])",
            "normalized": r"在授权环境中分析\1拦截机制的触发条件、判定逻辑、误报边界与防护改进建议",
            "category": "security_research",
            "risk": "medium",
            "notes": "regex 兜底规则，覆盖未单独枚举的拦截类表述",
            "match_type": "regex",
            "priority": 60,
        },
        {
            "term": r"绕过([^\s，。、“”：:（）()]{1,24}?)(?=的|方案|思路|方法|流程|步骤|机制|功能|策略|实现|$|[，。、“”：:（）()])",
            "normalized": r"在授权环境中评估\1相关机制的判定逻辑、约束边界、潜在误报与防护改进建议",
            "category": "security_research",
            "risk": "medium",
            "notes": "regex 宽泛兜底规则，覆盖未单独枚举的绕过类表述",
            "match_type": "regex",
            "priority": 90,
        },
    ],
}


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _platform_data_home(app_name: str) -> Path:
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / app_name
    if sys_platform() == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    return Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / app_name


def sys_platform() -> str:
    return os.uname().sysname.lower() if hasattr(os, "uname") else os.name


def default_data_home() -> Path:
    override = os.getenv("SECPROMPT_HOME", "").strip() or os.getenv("MCP_PRO_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    return _platform_data_home("secprompt")


def default_rule_file() -> Path:
    new_file = default_data_home() / "rules.json"
    if new_file.exists():
        return new_file

    old_file = _platform_data_home("mcp-pro") / "rules.json"
    if old_file.exists():
        new_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old_file, new_file)
    return new_file


@dataclass(frozen=True)
class Settings:
    rule_file: Path


@dataclass(frozen=True)
class RewriteDecision:
    status: str
    reason: str
    rewritten_prompt: str
    matched_terms: list[str]


@dataclass
class RuleStore:
    file_path: Path

    def __post_init__(self) -> None:
        self._lock = threading.Lock()
        self._ensure_exists()

    def _ensure_exists(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.save(DEFAULT_RULES)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize_payload(payload: dict) -> dict:
        result = {
            "version": int(payload.get("version", 1)),
            "updated_at": str(payload.get("updated_at", "")),
            "rules": payload.get("rules", []),
        }
        if not isinstance(result["rules"], list):
            raise ValueError("rules must be a list")
        return result

    @staticmethod
    def _validate_rule(rule: dict) -> dict[str, str]:
        term = str(rule.get("term", "")).strip()
        normalized = str(rule.get("normalized", "")).strip()
        category = str(rule.get("category", "general")).strip() or "general"
        risk = str(rule.get("risk", "low")).strip().lower() or "low"
        notes = str(rule.get("notes", "")).strip()
        match_type = str(rule.get("match_type", "literal")).strip().lower() or "literal"
        priority = int(rule.get("priority", 100))
        if not term:
            raise ValueError("term is required")
        if not normalized:
            raise ValueError("normalized is required")
        if risk not in {"low", "medium", "high"}:
            raise ValueError("risk must be one of: low, medium, high")
        if match_type not in {"literal", "regex"}:
            raise ValueError("match_type must be one of: literal, regex")
        return {
            "term": term,
            "normalized": normalized,
            "category": category,
            "risk": risk,
            "notes": notes,
            "match_type": match_type,
            "priority": priority,
        }

    def load(self) -> dict:
        self._ensure_exists()
        with self.file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return self._normalize_payload(data)

    def save(self, payload: dict) -> dict:
        normalized = self._normalize_payload(payload)
        normalized["rules"] = [self._validate_rule(item) for item in normalized["rules"]]
        normalized["updated_at"] = self._now_iso()

        tmp_file = self.file_path.with_suffix(".tmp")
        with tmp_file.open("w", encoding="utf-8") as handle:
            json.dump(normalized, handle, ensure_ascii=False, indent=2)
        tmp_file.replace(self.file_path)
        return normalized

    def list_rules(self, category: str = "", risk: str = "") -> dict:
        data = self.load()
        rules = data["rules"]
        if category:
            rules = [item for item in rules if item.get("category", "") == category]
        if risk:
            rules = [item for item in rules if item.get("risk", "") == risk]
        return {"updated_at": data["updated_at"], "rules": rules}

    def upsert_rule(self, rule: dict) -> tuple[str, dict]:
        checked = self._validate_rule(rule)
        with self._lock:
            data = self.load()
            items = data["rules"]
            index = next((i for i, item in enumerate(items) if item["term"] == checked["term"]), -1)
            if index >= 0:
                items[index] = checked
                action = "updated"
            else:
                items.append(checked)
                action = "created"
            saved = self.save(data)
            current = next(item for item in saved["rules"] if item["term"] == checked["term"])
        return action, current

    def delete_rule(self, term: str) -> bool:
        term = term.strip()
        if not term:
            raise ValueError("term is required")
        with self._lock:
            data = self.load()
            before = len(data["rules"])
            data["rules"] = [item for item in data["rules"] if item["term"] != term]
            if len(data["rules"]) == before:
                return False
            self.save(data)
            return True

    def bulk_import(self, rules: list[dict], mode: str = "merge") -> dict[str, int]:
        if mode not in {"merge", "replace"}:
            raise ValueError("mode must be merge or replace")
        checked = [self._validate_rule(item) for item in rules]
        created = 0
        updated = 0

        with self._lock:
            data = self.load()
            if mode == "replace":
                data["rules"] = checked
                created = len(checked)
                self.save(data)
                return {"created": created, "updated": updated}

            index_map = {item["term"]: idx for idx, item in enumerate(data["rules"])}
            for item in checked:
                idx = index_map.get(item["term"])
                if idx is None:
                    data["rules"].append(item)
                    index_map[item["term"]] = len(data["rules"]) - 1
                    created += 1
                else:
                    data["rules"][idx] = item
                    updated += 1
            self.save(data)
        return {"created": created, "updated": updated}


def load_settings() -> Settings:
    rule_file_env = os.getenv("SECPROMPT_RULE_FILE", "").strip() or os.getenv("MCP_RULE_FILE", "").strip()
    rule_file = Path(rule_file_env).expanduser() if rule_file_env else default_rule_file()
    return Settings(rule_file=rule_file)


def infer_platform(raw_text: str) -> str:
    text = raw_text.lower()
    if any(token in text for token in ["wkwebview", "webview", "flutter", "react native", "rn bridge", "js bridge"]):
        return "hybrid"
    if any(token in text for token in ["ios", "ipa", "bundle id", "nsurlsession", "keychain", "sectrust"]):
        return "ios"
    if any(token in text for token in ["android", "apk", "aab", "okhttp", "retrofit", "jni", "frida"]):
        return "android"
    if "http://" in text or "https://" in text:
        return "web"
    if re.search(r"(?<!@)\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b", text):
        return "web"
    return "generic"


def resolve_platform(platform_arg: str, raw_text: str) -> str:
    value = (platform_arg or "").strip().lower()
    if not value or value == "auto":
        return infer_platform(raw_text)
    if value not in SUPPORTED_PLATFORMS:
        return "generic"
    return value


def _stage_contract() -> str:
    return (
        "每个阶段必须包含 5 项：\n"
        "- Confirmed facts\n"
        "- Key evidence\n"
        "- Current inference\n"
        "- Unverified points\n"
        "- Next step"
    )


def build_platform_reverse_request(raw_request: str, platform: str, focus_param: str = "") -> str:
    focus_text = focus_param.strip() or "目标参数"
    if platform == "web":
        guide = (
            "【平台】Web\n"
            f"【逆向测试重点】还原 {focus_text} 的生成链路并评估强度（仅防御性分析）\n"
            "按阶段执行：\n"
            "1. Recon（触发动作与请求序列）\n"
            "2. Communication Analysis（URL/headers/cookie/参数变化）\n"
            "3. Static Analysis（签名与依赖函数链）\n"
            "4. Dynamic Validation（关键中间值证据点）\n"
            "5. Reconstruction & Strength Assessment（0-10评分+改进建议）\n"
        )
    elif platform == "ios":
        guide = (
            "【平台】iOS\n"
            f"【逆向测试重点】还原 {focus_text} 的生成链路并评估强度（仅防御性分析）\n"
            "按阶段执行：\n"
            "1. Recon（关键页面/调用路径）\n"
            "2. Communication Analysis（NSURLSession/请求构建）\n"
            "3. Static Analysis（签名函数、SecTrust、Keychain、WKWebView）\n"
            "4. Dynamic Validation（入参/出参/中间值证据点）\n"
            "5. Reconstruction & Strength Assessment（0-10评分+改进建议）\n"
        )
    elif platform == "android":
        guide = (
            "【平台】Android\n"
            f"【逆向测试重点】还原 {focus_text} 的生成链路并评估强度（仅防御性分析）\n"
            "按阶段执行：\n"
            "1. Recon（关键页面/组件路径）\n"
            "2. Communication Analysis（okhttp/retrofit/请求构建）\n"
            "3. Static Analysis（Java/Kotlin到JNI/so关键链路）\n"
            "4. Dynamic Validation（入参/出参/中间值证据点）\n"
            "5. Reconstruction & Strength Assessment（0-10评分+改进建议）\n"
        )
    elif platform == "hybrid":
        guide = (
            "【平台】Hybrid\n"
            f"【逆向测试重点】还原 {focus_text} 在 H5 与 Native 跨层链路中的生成过程（仅防御性分析）\n"
            "按阶段执行：\n"
            "1. Recon（入口页面与桥接触发点）\n"
            "2. Communication Analysis（H5请求与Native参与边界）\n"
            "3. Static Analysis（WebView/WKWebView/Bridge路径）\n"
            "4. Dynamic Validation（跨层参数映射证据点）\n"
            "5. Reconstruction & Strength Assessment（0-10评分+改进建议）\n"
        )
    else:
        guide = (
            "【平台】待识别\n"
            f"【逆向测试重点】还原 {focus_text} 的生成链路并评估强度（仅防御性分析）\n"
            "先识别目标平台（Web/iOS/Android/Hybrid），再按对应平台流程执行。\n"
        )

    return (
        "你是内部应用安全逆向测试助手，仅做授权防御性评估，不提供攻击利用细节。\n"
        f"{guide}\n"
        f"{_stage_contract()}\n"
        f"【用户原始任务】{raw_request}"
    )


def contains_high_risk(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in HIGH_RISK_PATTERNS)


def rewrite_text(raw_text: str, rules: list[dict]) -> tuple[str, list[str]]:
    rewritten = raw_text
    matched: list[str] = []
    ordered_rules = sorted(
        rules,
        key=lambda item: (int(item.get("priority", 100)), item.get("match_type", "literal") == "regex", -len(item["term"])),
    )
    for rule in ordered_rules:
        term = rule["term"]
        replacement = rule["normalized"]
        if rule.get("match_type", "literal") == "regex":
            pattern = re.compile(term, re.IGNORECASE)
        else:
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
    target_owner: str,
    authorization_evidence: str,
    test_scope: str,
    rules: list[dict],
    output_format: str = "步骤清单",
    language: str = "zh-CN",
) -> RewriteDecision:
    missing_fields: list[str] = []
    if not target_owner.strip():
        missing_fields.append("target_owner")
    if not authorization_evidence.strip():
        missing_fields.append("authorization_evidence")
    if not test_scope.strip():
        missing_fields.append("test_scope")
    if missing_fields:
        return RewriteDecision(
            status="blocked",
            reason=f"缺少必要字段: {', '.join(missing_fields)}。必须提供目标归属、授权证明、测试范围。",
            rewritten_prompt="",
            matched_terms=[],
        )

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
        f"目标归属: {target_owner}\n"
        f"授权证明: {authorization_evidence}\n"
        f"测试范围: {test_scope}\n"
        f"附加范围说明: {scope}\n"
        f"用户原始需求: {raw_request}\n"
        f"语义规范化后需求: {rewritten_text}\n"
        "输出边界: 只提供防御性分析、审计流程、修复建议、风险评估，不提供攻击执行细节或绕过安全机制的方法。\n"
        f"输出格式: {output_format}"
    )
    return RewriteDecision(
        status="ok",
        reason="rewritten",
        rewritten_prompt=prompt,
        matched_terms=matched_terms,
    )


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
    parser = argparse.ArgumentParser(description="Codex skill wrapper for local secprompt workflows")
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
    p_upsert.add_argument("--match-type", default="literal", choices=["literal", "regex"])
    p_upsert.add_argument("--priority", type=int, default=100)

    p_delete = sub.add_parser("rule-delete", help="Delete one rule")
    p_delete.add_argument("--term", required=True)

    p_bulk = sub.add_parser("rule-bulk-import", help="Bulk import rules from JSON file")
    p_bulk.add_argument("--file", required=True, help="Path to JSON file with {\"rules\": [...]} ")
    p_bulk.add_argument("--mode", default="merge", choices=["merge", "replace"])

    p_test = sub.add_parser("rule-test", help="Preview how the current rules normalize text")
    p_test.add_argument("--raw-text", required=True)

    p_rewrite = sub.add_parser("rewrite", help="Rewrite one request using the local secprompt logic")
    p_rewrite.add_argument("--raw-request", required=True)
    p_rewrite.add_argument("--purpose", default="授权安全研究")
    p_rewrite.add_argument("--scope", default="授权测试环境")
    p_rewrite.add_argument("--platform", default="auto", choices=["auto", "web", "ios", "android", "hybrid", "generic"])
    p_rewrite.add_argument("--focus-param", default="")
    p_rewrite.add_argument("--target-owner", default="")
    p_rewrite.add_argument("--authorization-evidence", default="")
    p_rewrite.add_argument("--test-scope", default="")
    p_rewrite.add_argument("--authorized", dest="authorized", action="store_true", default=True)
    p_rewrite.add_argument("--no-authorized", dest="authorized", action="store_false")
    p_rewrite.add_argument("--output-format", default="步骤清单")
    p_rewrite.add_argument("--language", default="zh-CN")

    return parser


def store() -> RuleStore:
    return RuleStore(load_settings().rule_file)


def cmd_init(args: argparse.Namespace) -> int:
    rule_store = store()
    if args.reset_default:
        rule_store.save(DEFAULT_RULES)
    data = rule_store.load()
    print_json({
        "status": "ok",
        "rule_file": str(rule_store.file_path),
        "rules_count": len(data["rules"]),
        "updated_at": data["updated_at"],
    })
    return 0


def cmd_rule_path(_: argparse.Namespace) -> int:
    rule_store = store()
    data = rule_store.load()
    print_json({
        "rule_file": str(rule_store.file_path),
        "rules_count": len(data["rules"]),
        "updated_at": data["updated_at"],
    })
    return 0


def cmd_rule_list(args: argparse.Namespace) -> int:
    print_json(store().list_rules(category=args.category, risk=args.risk))
    return 0


def cmd_rule_upsert(args: argparse.Namespace) -> int:
    action, rule = store().upsert_rule({
        "term": args.term,
        "normalized": args.normalized,
        "category": args.category,
        "risk": args.risk,
        "notes": args.notes,
        "match_type": args.match_type,
        "priority": args.priority,
    })
    print_json({"status": "ok", "action": action, "rule": rule})
    return 0


def cmd_rule_delete(args: argparse.Namespace) -> int:
    deleted = store().delete_rule(args.term)
    print_json({"status": "ok" if deleted else "not_found", "term": args.term})
    return 0


def cmd_rule_bulk_import(args: argparse.Namespace) -> int:
    with open(args.file, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    rules = payload.get("rules")
    if not isinstance(rules, list):
        raise ValueError("导入文件必须包含 `rules` 列表。")
    summary = store().bulk_import(rules=rules, mode=args.mode)
    print_json({"status": "ok", "mode": args.mode, **summary})
    return 0


def cmd_rule_test(args: argparse.Namespace) -> int:
    rule_store = store()
    decision = build_compliant_prompt(
        raw_request=args.raw_text,
        purpose="测试规则命中情况",
        authorized=True,
        scope="本地测试",
        target_owner="本地测试目标",
        authorization_evidence="本地开发者自测",
        test_scope="仅限本地测试文本",
        rules=rule_store.load()["rules"],
    )
    print_json({
        "status": decision.status,
        "reason": decision.reason,
        "matched_terms": decision.matched_terms,
        "rewritten_preview": decision.rewritten_prompt,
    })
    return 0


def cmd_rewrite(args: argparse.Namespace) -> int:
    raw_prompt = args.raw_request.strip()
    platform = resolve_platform(args.platform, raw_prompt)
    routed_prompt = build_platform_reverse_request(raw_prompt, platform, args.focus_param)
    target_owner, authorization_evidence, test_scope = _resolve_defaults(args, raw_prompt)
    rule_store = store()
    decision = build_compliant_prompt(
        raw_request=routed_prompt,
        purpose=args.purpose,
        authorized=args.authorized,
        scope=args.scope,
        target_owner=target_owner,
        authorization_evidence=authorization_evidence,
        test_scope=test_scope,
        rules=rule_store.load()["rules"],
        output_format=args.output_format,
        language=args.language,
    )
    print_json({
        "status": decision.status,
        "reason": decision.reason,
        "platform": platform,
        "matched_terms": decision.matched_terms,
        "rewritten_prompt": decision.rewritten_prompt,
        "rule_file": str(rule_store.file_path),
    })
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

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RULES: dict[str, Any] = {
    "version": 1,
    "updated_at": "",
    "rules": [
        {
            "term": "逆向",
            "normalized": "在授权环境下进行二进制行为分析",
            "category": "security_research",
            "risk": "medium",
            "notes": "强调合法授权和分析导向",
        },
        {
            "term": "破解",
            "normalized": "在授权范围内进行安全性评估",
            "category": "security_research",
            "risk": "high",
            "notes": "高风险词，通常需人工复核",
        },
    ],
}


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
    def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        result = {
            "version": int(payload.get("version", 1)),
            "updated_at": str(payload.get("updated_at", "")),
            "rules": payload.get("rules", []),
        }
        if not isinstance(result["rules"], list):
            raise ValueError("rules must be a list")
        return result

    @staticmethod
    def _validate_rule(rule: dict[str, Any]) -> dict[str, str]:
        term = str(rule.get("term", "")).strip()
        normalized = str(rule.get("normalized", "")).strip()
        category = str(rule.get("category", "general")).strip() or "general"
        risk = str(rule.get("risk", "low")).strip().lower() or "low"
        notes = str(rule.get("notes", "")).strip()
        if not term:
            raise ValueError("term is required")
        if not normalized:
            raise ValueError("normalized is required")
        if risk not in {"low", "medium", "high"}:
            raise ValueError("risk must be one of: low, medium, high")
        return {
            "term": term,
            "normalized": normalized,
            "category": category,
            "risk": risk,
            "notes": notes,
        }

    def load(self) -> dict[str, Any]:
        self._ensure_exists()
        with self.file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return self._normalize_payload(data)

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_payload(payload)
        rules = [self._validate_rule(item) for item in normalized["rules"]]
        normalized["rules"] = rules
        normalized["updated_at"] = self._now_iso()

        tmp_file = self.file_path.with_suffix(".tmp")
        with tmp_file.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
        tmp_file.replace(self.file_path)
        return normalized

    def list_rules(self, category: str = "", risk: str = "") -> dict[str, Any]:
        data = self.load()
        rules = data["rules"]
        if category:
            rules = [r for r in rules if r.get("category", "") == category]
        if risk:
            rules = [r for r in rules if r.get("risk", "") == risk]
        return {"updated_at": data["updated_at"], "rules": rules}

    def upsert_rule(self, rule: dict[str, Any]) -> tuple[str, dict[str, Any]]:
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

    def bulk_import(self, rules: list[dict[str, Any]], mode: str = "merge") -> dict[str, int]:
        if mode not in {"merge", "replace"}:
            raise ValueError("mode must be merge or replace")
        checked = [self._validate_rule(r) for r in rules]
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


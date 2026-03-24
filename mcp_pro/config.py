from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mcp_pro.paths import default_rule_file


@dataclass(frozen=True)
class Settings:
    rule_file: Path
    log_level: str


def load_settings() -> Settings:
    rule_file_env = os.getenv("SECPROMPT_RULE_FILE", "").strip() or os.getenv("MCP_RULE_FILE", "").strip()
    rule_file = Path(rule_file_env).expanduser() if rule_file_env else default_rule_file()
    log_level = (os.getenv("SECPROMPT_LOG_LEVEL", "").strip() or os.getenv("MCP_LOG_LEVEL", "INFO")).upper()
    return Settings(
        rule_file=rule_file,
        log_level=log_level,
    )

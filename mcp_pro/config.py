from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mcp_pro.paths import default_rule_file


@dataclass(frozen=True)
class Settings:
    admin_token: str
    rule_file: Path
    log_level: str


def load_settings() -> Settings:
    admin_token = os.getenv("MCP_ADMIN_TOKEN", "").strip()
    rule_file_env = os.getenv("MCP_RULE_FILE", "").strip()
    rule_file = Path(rule_file_env).expanduser() if rule_file_env else default_rule_file()
    log_level = os.getenv("MCP_LOG_LEVEL", "INFO").upper()
    return Settings(
        admin_token=admin_token,
        rule_file=rule_file,
        log_level=log_level,
    )

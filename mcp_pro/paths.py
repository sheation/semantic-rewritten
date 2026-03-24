from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_dir


def default_data_home() -> Path:
    """
    Resolve user-writable data directory for mcp-pro.

    Priority:
    1) MCP_PRO_HOME env
    2) platform default user data dir
    """
    override = os.getenv("MCP_PRO_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    return Path(user_data_dir("mcp-pro", "mcp-pro")).expanduser()


def default_rule_file() -> Path:
    return default_data_home() / "rules.json"


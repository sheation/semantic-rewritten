from __future__ import annotations

import os
import shutil
from pathlib import Path

from platformdirs import user_data_dir


def default_data_home() -> Path:
    """
    Resolve user-writable data directory for secprompt.

    Priority:
    1) SECPROMPT_HOME env
    2) MCP_PRO_HOME env (compat)
    2) platform default user data dir
    """
    override = os.getenv("SECPROMPT_HOME", "").strip() or os.getenv("MCP_PRO_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    return Path(user_data_dir("secprompt", "secprompt")).expanduser()


def default_rule_file() -> Path:
    new_file = default_data_home() / "rules.json"
    if new_file.exists():
        return new_file

    old_file = Path(user_data_dir("mcp-pro", "mcp-pro")).expanduser() / "rules.json"
    if old_file.exists():
        new_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old_file, new_file)
    return new_file

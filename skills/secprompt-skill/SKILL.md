---
name: secprompt-skill
description: >
  Use when Codex needs the local secprompt semantic-rewrite workflow without calling an MCP server.
  Supports rewriting security-research requests, testing rule matches, initializing the rule store,
  and managing rules.json by reusing the Python logic from this repository.
---

# Secprompt Skill

Use this skill as a local wrapper around the repository's existing Python logic. Do not treat it as a replacement for the MCP server.

## Use It For

- Run secprompt logic directly inside Codex conversations
- Manage the local rule file without an MCP host
- Validate or ship the repository as a Codex skill

## Follow These Rules

- Keep `mcp_pro/` as the single source of truth for business logic
- Prefer `scripts/secprompt_skill.py` over reimplementing logic in the conversation
- Avoid changing `rewriter.py`, `rule_store.py`, or `platform_router.py` unless the user explicitly asks for behavior changes

## Run It

If `.venv` exists in the repository root, prefer:

```bash
.venv/bin/python skills/secprompt-skill/scripts/secprompt_skill.py <subcommand> ...
```

Otherwise use:

```bash
python3 skills/secprompt-skill/scripts/secprompt_skill.py <subcommand> ...
```

## Common Commands

Initialize the rule file:

```bash
python3 skills/secprompt-skill/scripts/secprompt_skill.py init
python3 skills/secprompt-skill/scripts/secprompt_skill.py init --reset-default
```

Inspect or manage rules:

```bash
python3 skills/secprompt-skill/scripts/secprompt_skill.py rule-path
python3 skills/secprompt-skill/scripts/secprompt_skill.py rule-list --category security_research
python3 skills/secprompt-skill/scripts/secprompt_skill.py rule-upsert \
  --term "逆向分析" \
  --normalized "在授权环境下进行程序行为与协议分析" \
  --category security_research \
  --risk medium
python3 skills/secprompt-skill/scripts/secprompt_skill.py rule-delete --term "逆向分析"
python3 skills/secprompt-skill/scripts/secprompt_skill.py rule-bulk-import --file samples/rules_import_example.json
python3 skills/secprompt-skill/scripts/secprompt_skill.py rule-test --raw-text "请给我逆向某协议的步骤"
```

Rewrite a request:

```bash
python3 skills/secprompt-skill/scripts/secprompt_skill.py rewrite \
  --raw-request "分析 completion 接口参数生成链路" \
  --platform web \
  --focus-param a_bogus
```

## Read the Output

- Expect JSON output from every subcommand
- Read `rewritten_prompt` when `rewrite` returns `status=ok`
- Read `status` and `reason` when `rewrite` is blocked
- Treat rule-management output as the direct result from the underlying storage layer

## Install It

Install by copying or linking `skills/secprompt-skill/` into the active Codex skill directory. In this repository, the intended install target is `$CODEX_HOME/skills/secprompt-skill`.

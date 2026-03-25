---
name: secprompt-skill
description: >
  Use when Codex needs a local semantic-rewrite skill for authorized security-research workflows.
  Supports rewriting requests, testing rule matches, initializing the rule store, and managing
  rules.json through a self-contained local script with no MCP server dependency.
---

# Secprompt Skill

Use this skill to run local semantic-rewrite workflows for authorized security research. Treat the repository root as the skill directory.

## Use It For

- Rewrite a request into a clearer, bounded security-research prompt
- Initialize and inspect the local rule store
- Add, update, delete, or bulk-import normalization rules
- Test how the current rules rewrite a specific text

## Follow These Rules

- Run `scripts/secprompt_skill.py` instead of reimplementing rule logic in the conversation
- Return the JSON fields that the script emits instead of paraphrasing away important status values
- Treat `status != ok` as an explicit block or review signal
- Keep rule changes local to the user's declared environment and workflow

## Run It

Prefer:

```bash
python3 scripts/secprompt_skill.py <subcommand> ...
```

## Common Commands

Initialize the rule file:

```bash
python3 scripts/secprompt_skill.py init
python3 scripts/secprompt_skill.py init --reset-default
```

Inspect or manage rules:

```bash
python3 scripts/secprompt_skill.py rule-path
python3 scripts/secprompt_skill.py rule-list --category security_research
python3 scripts/secprompt_skill.py rule-upsert \
  --term "逆向分析" \
  --normalized "在授权环境下进行程序行为与协议分析" \
  --category security_research \
  --risk medium
python3 scripts/secprompt_skill.py rule-delete --term "逆向分析"
python3 scripts/secprompt_skill.py rule-bulk-import --file samples/rules_import_example.json
python3 scripts/secprompt_skill.py rule-test --raw-text "请给我逆向某协议的步骤"
```

Rewrite a request:

```bash
python3 scripts/secprompt_skill.py rewrite \
  --raw-request "分析 completion 接口参数生成链路" \
  --platform web \
  --focus-param a_bogus
```

## Read the Output

- Every subcommand returns JSON
- Read `rewritten_prompt` when `status=ok`
- Read `reason` when `status` is `blocked`, `needs_review`, or `error`
- Use `rule_file` to confirm which local rule store is active

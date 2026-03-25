# secprompt-skill

`secprompt-skill` 是一个给 Codex 使用的本地 skill。

它提供两类能力：

- 请求改写：把安全研究需求改写成边界更清晰的授权研究请求
- 规则管理：初始化、查看、增删改、批量导入本地规则库

## 仓库结构

```text
.
├─ SKILL.md
├─ agents/
│  └─ openai.yaml
├─ scripts/
│  └─ secprompt_skill.py
├─ samples/
│  └─ rules_import_example.json
└─ README.md
```

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/sheation/semantic-rewritten.git
cd semantic-rewritten
```

### 2. 安装到 Codex skills 目录

如果当前环境设置了 `CODEX_HOME`：

```bash
mkdir -p "$CODEX_HOME/skills"
ln -s "$(pwd)" "$CODEX_HOME/skills/secprompt-skill"
```

如果没有设置 `CODEX_HOME`：

```bash
mkdir -p ~/.codex/skills
ln -s "$(pwd)" ~/.codex/skills/secprompt-skill
```

安装完成后，Codex 会把这个仓库识别为 `secprompt-skill`。

## 使用

在 Codex 中显式调用：

```text
Use $secprompt-skill to rewrite this request for an authorized security review.
```

也可以直接运行附带脚本：

```bash
python3 scripts/secprompt_skill.py <subcommand> ...
```

支持的子命令：

- `init`
- `rule-path`
- `rule-list`
- `rule-upsert`
- `rule-delete`
- `rule-bulk-import`
- `rule-test`
- `rewrite`

## 示例

初始化规则文件：

```bash
python3 scripts/secprompt_skill.py init
python3 scripts/secprompt_skill.py init --reset-default
```

查看规则：

```bash
python3 scripts/secprompt_skill.py rule-path
python3 scripts/secprompt_skill.py rule-list --category security_research
```

测试规则命中：

```bash
python3 scripts/secprompt_skill.py rule-test \
  --raw-text "请给我逆向某协议的步骤"
```

改写请求：

```bash
python3 scripts/secprompt_skill.py rewrite \
  --raw-request "分析 completion 接口参数生成链路" \
  --platform web \
  --focus-param a_bogus
```

批量导入规则：

```bash
python3 scripts/secprompt_skill.py rule-bulk-import \
  --file samples/rules_import_example.json \
  --mode merge
```

## 配置

默认情况下，规则文件会写到用户目录下，而不是仓库内。

可用环境变量：

- `SECPROMPT_RULE_FILE`
- `SECPROMPT_HOME`
- `SECPROMPT_DEFAULT_TARGET_OWNER`
- `SECPROMPT_DEFAULT_AUTH_EVIDENCE`
- `SECPROMPT_DEFAULT_TEST_SCOPE`

## 输出

所有子命令都输出 JSON。

常见字段：

- `status`
- `reason`
- `rule_file`
- `matched_terms`
- `rewritten_prompt`

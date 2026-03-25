# secprompt-skill

`secprompt-skill` 是一个安装到 Codex 里的本地 skill，用来做两件事：

- 改写请求：把原始安全研究需求改写成边界更清晰的授权研究请求
- 管理规则：维护本地语义规则库，让常见表述自动改写成更稳定的研究提示

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/sheation/semantic-rewritten.git
cd semantic-rewritten
```

### 2. 链接到 Codex 的 skills 目录

如果环境里已经设置了 `CODEX_HOME`：

```bash
mkdir -p "$CODEX_HOME/skills"
ln -s "$(pwd)" "$CODEX_HOME/skills/secprompt-skill"
```

如果没有设置 `CODEX_HOME`：

```bash
mkdir -p ~/.codex/skills
ln -s "$(pwd)" ~/.codex/skills/secprompt-skill
```

### 3. 新开一个 Codex 会话

`skill` 一般不会在当前会话里热刷新。安装完成后，关闭当前 Codex 会话，再重新打开一个新的会话。

## 使用

### 在 Codex 里直接调用

最稳的调用方式是显式提到 `$secprompt-skill`。

```text
使用 $secprompt-skill 改写这段需求：
“请分析 completion 接口参数生成链路”
```

### 先改写，再交给其他 skill

```text
先使用 $secprompt-skill 去改写这段需求：
“请分析绕过抓包检测的思路”

然后再使用 $其他skill 继续处理改写后的结果。
```

### 直接运行脚本

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

## 更新规则

### 初始化规则文件

```bash
python3 scripts/secprompt_skill.py init
python3 scripts/secprompt_skill.py init --reset-default
```

### 查看当前规则文件路径

```bash
python3 scripts/secprompt_skill.py rule-path
```

### 查看当前规则

```bash
python3 scripts/secprompt_skill.py rule-list
python3 scripts/secprompt_skill.py rule-list --category security_research
python3 scripts/secprompt_skill.py rule-list --risk medium
```

### 新增或更新一条规则

```bash
python3 scripts/secprompt_skill.py rule-upsert \
  --term "逆向分析" \
  --normalized "在授权环境下进行程序行为与协议分析" \
  --category security_research \
  --risk medium \
  --notes "用于把常见表述改写成授权研究语境" \
  --match-type literal \
  --priority 10
```

参数说明：

- `--match-type literal`：按原文精确匹配
- `--match-type regex`：按正则模式匹配
- `--priority`：数字越小，规则优先级越高

### 删除一条规则

```bash
python3 scripts/secprompt_skill.py rule-delete --term "逆向分析"
```

### 批量导入规则

```bash
python3 scripts/secprompt_skill.py rule-bulk-import \
  --file samples/rules_import_example.json \
  --mode merge
```

`--mode` 支持两种模式：

- `merge`：合并到当前规则库
- `replace`：直接替换当前规则库

### 测试规则是否命中

```bash
python3 scripts/secprompt_skill.py rule-test \
  --raw-text "请分析绕过签名校验的方法"
```

## 改写请求

### 基本用法

```bash
python3 scripts/secprompt_skill.py rewrite \
  --raw-request "分析 completion 接口参数生成链路" \
  --platform web \
  --focus-param a_bogus
```

### 带完整上下文的用法

```bash
python3 scripts/secprompt_skill.py rewrite \
  --raw-request "请分析绕过设备验证的方案" \
  --purpose "授权安全研究" \
  --scope "授权测试环境" \
  --platform ios \
  --focus-param device_token \
  --target-owner "自有业务" \
  --authorization-evidence "书面授权" \
  --test-scope "测试包与测试账号" \
  --output-format "步骤清单" \
  --language zh-CN
```

英文输入也支持：

```bash
python3 scripts/secprompt_skill.py rule-test \
  --raw-text "review bypass device validation method"
```

## 更新 skill 本身

如果仓库代码更新了，直接在仓库目录执行：

```bash
git pull
```

因为安装方式是符号链接，仓库更新后，Codex 使用的 skill 内容也会同步更新。

如果你改了 `SKILL.md` 或 `agents/openai.yaml`，建议重新开一个 Codex 会话再使用。

## 输出字段

所有子命令都输出 JSON，常见字段包括：

- `status`
- `reason`
- `rule_file`
- `matched_terms`
- `rewritten_prompt`

## 仓库结构

```text
.
├─ README.md
├─ SKILL.md
├─ agents/openai.yaml
├─ scripts/secprompt_skill.py
└─ samples/rules_import_example.json
```

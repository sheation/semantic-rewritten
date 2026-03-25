# secprompt

`secprompt` 是一个面向安全研究场景的语义重写工具集。  
它把原始请求规范化为更清晰、边界明确、便于审计的表达，并支持两种交付形态：

- `MCP Server`：供 Codex 或其他 MCP host 以工具方式调用
- `Codex Skill`：供 Codex 直接在本地工作流中复用同一套逻辑

## 功能概览

- 请求改写：把原始需求重写为边界更清晰的研究请求
- 规则管理：支持列出、新增、删除、批量导入规则
- 平台路由：支持 `web`、`ios`、`android`、`hybrid`、`generic`
- 本地规则存储：默认使用用户可写目录，便于分发和持久化
- Codex 包装：支持先改写再调用 `codex`
- Skill 封装：支持作为 Codex skill 直接使用本地逻辑

## MCP 和 Skill 的区别

- `MCP` 是服务接口
  - 通过标准工具协议暴露 `rewrite_request`、`rule_list`、`rule_upsert` 等能力
  - 适合被 Codex、IDE 或其他 Agent 当作工具调用
- `Skill` 是 Codex 能力包
  - 通过 `SKILL.md + scripts/` 提供工作流和本地脚本
  - 不对外暴露 MCP 工具协议
  - 适合让 Codex 在本地直接复用仓库逻辑

这个仓库同时保留两者。底层逻辑只维护一份，位于 `mcp_pro/`。

## 项目结构

```text
.
├─ mcp_pro/
│  ├─ server_app.py       # MCP 服务入口
│  ├─ rewriter.py         # 请求改写逻辑
│  ├─ rule_store.py       # 规则读写与校验
│  ├─ platform_router.py  # 平台识别与路由模板
│  ├─ rules_cli.py        # 规则管理 CLI
│  ├─ codex_rewrite_cli.py
│  └─ init_cli.py
├─ skills/
│  └─ secprompt-skill/
│     ├─ SKILL.md
│     └─ scripts/
│        └─ secprompt_skill.py
├─ data/rules.json
├─ samples/rules_import_example.json
├─ pyproject.toml
└─ server.py
```

## 安装

### 方式 1：源码安装

```bash
git clone https://github.com/sheation/semantic-rewritten.git
cd semantic-rewritten
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 方式 2：直接从 GitHub 安装

```bash
pip install "git+https://github.com/sheation/semantic-rewritten.git"
```

## MCP 用法

### 初始化规则文件

```bash
secprompt-setup
```

### 启动 MCP 服务

```bash
secprompt-server
```

### 注册到 Codex

```bash
codex mcp add semantic-rewriter -- "$(which secprompt-server)"
```

### 检查或删除注册

```bash
codex mcp list
codex mcp get semantic-rewriter --json
codex mcp remove semantic-rewriter
```

### MCP 暴露的工具

- `health`
- `rule_list`
- `rule_upsert`
- `rule_delete`
- `rule_bulk_import`
- `rule_test`
- `rewrite_request`

## Codex Skill 用法

### Skill 目录

仓库内 skill 路径：

```text
skills/secprompt-skill
```

### 安装到 Codex

如果当前环境设置了 `CODEX_HOME`，将 skill 链接到：

```bash
ln -s "$(pwd)/skills/secprompt-skill" "$CODEX_HOME/skills/secprompt-skill"
```

如果没有设置 `CODEX_HOME`，通常使用默认目录：

```bash
mkdir -p ~/.codex/skills
ln -s "$(pwd)/skills/secprompt-skill" ~/.codex/skills/secprompt-skill
```

### 在 Codex 中触发 skill

示例提示词：

```text
Use $secprompt-skill to rewrite this request for an authorized security review.
```

### 直接运行 skill 脚本

如果仓库根目录下存在 `.venv`：

```bash
.venv/bin/python skills/secprompt-skill/scripts/secprompt_skill.py <subcommand> ...
```

否则：

```bash
python3 skills/secprompt-skill/scripts/secprompt_skill.py <subcommand> ...
```

### Skill 支持的子命令

- `init`
- `rule-path`
- `rule-list`
- `rule-upsert`
- `rule-delete`
- `rule-bulk-import`
- `rule-test`
- `rewrite`

### Skill 示例

初始化规则文件：

```bash
python3 skills/secprompt-skill/scripts/secprompt_skill.py init
python3 skills/secprompt-skill/scripts/secprompt_skill.py init --reset-default
```

查看规则：

```bash
python3 skills/secprompt-skill/scripts/secprompt_skill.py rule-path
python3 skills/secprompt-skill/scripts/secprompt_skill.py rule-list --category security_research
```

测试规则命中：

```bash
python3 skills/secprompt-skill/scripts/secprompt_skill.py rule-test \
  --raw-text "请给我逆向某协议的步骤"
```

执行请求改写：

```bash
python3 skills/secprompt-skill/scripts/secprompt_skill.py rewrite \
  --raw-request "分析 completion 接口参数生成链路" \
  --platform web \
  --focus-param a_bogus
```

## Codex 包装命令

可选：使用包装命令先改写再调用 `codex`：

```bash
secprompt-codex "请给我逆向某协议的步骤"
secprompt-codex --dry-run "请给我逆向某协议的步骤"
secprompt-codex --always-rewrite "请分析这个需求"
```

分平台逆向测试：

```bash
secprompt-codex --platform web --focus-param a_bogus "分析 completion 接口参数生成链路"
secprompt-codex --platform ios --focus-param sign_x "分析 iOS 客户端参数生成链路"
secprompt-codex --platform android --focus-param sign_x "分析 Android 客户端参数生成链路"
secprompt-codex --platform hybrid --focus-param token_y "分析 H5 + Native 跨层参数链路"
```

说明：

- `--platform auto` 会自动识别平台
- 平台模板按 `Recon -> Communication -> Static -> Dynamic -> Reconstruction` 输出
- 每个阶段都要求输出证据项

默认字段：

- `target_owner`: `用户声明的授权目标`
- `authorization_evidence`: `用户声明已获得合法授权`
- `test_scope`: 自动从输入中提取网址或域名，提取不到时使用默认范围

覆盖默认值示例：

```bash
secprompt-codex \
  --target-owner "公司自有系统" \
  --authorization-evidence "内部授权单 SEC-2026-001" \
  --test-scope "仅限 example.com /api/sign/*，2026-03-24 至 2026-03-31" \
  "请分析签名参数生成流程"
```

## 规则管理 CLI

查看当前规则文件路径：

```bash
secprompt-rules path
```

新增或更新一条规则：

```bash
secprompt-rules upsert \
  --term "逆向分析" \
  --normalized "在授权环境下进行程序行为与协议分析" \
  --category security_research \
  --risk medium \
  --notes "新增术语"
```

删除规则：

```bash
secprompt-rules delete --term "逆向分析"
```

批量导入规则：

```bash
secprompt-rules bulk-import \
  --file samples/rules_import_example.json \
  --mode merge
```

列出规则：

```bash
secprompt-rules list
```

## 配置项

- `SECPROMPT_RULE_FILE`：自定义规则文件路径
- `SECPROMPT_HOME`：覆盖默认数据目录
- `SECPROMPT_LOG_LEVEL`：日志级别，默认 `INFO`
- `SECPROMPT_DEFAULT_TARGET_OWNER`：`secprompt-codex` 默认目标归属
- `SECPROMPT_DEFAULT_AUTH_EVIDENCE`：`secprompt-codex` 默认授权证明
- `SECPROMPT_DEFAULT_TEST_SCOPE`：提取不到域名时的默认测试范围
- `SECPROMPT_REPO_ROOT`：skill 脚本定位仓库根目录时可选覆盖

## 开发说明

- `mcp_pro/` 是唯一业务逻辑来源
- `skills/secprompt-skill/` 只做 skill 封装，不重复实现核心规则
- 如果改动改写逻辑，应同时验证 MCP 和 skill 两条路径

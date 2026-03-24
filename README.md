# secprompt

一个面向安全研究场景的语义重写 MCP Server。  
它会把原始请求规范化为更清晰、边界明确、便于审计的表达。

## 功能概览

- 提供 MCP 工具：请求改写、规则管理、健康检查。
- 规则文件支持本地热更新，无需改代码。
- 默认将规则存放到用户可写目录，便于分发给不同使用者。
- 提供 `secprompt-codex` 包装命令，可先改写再调用 `codex`。

## 项目结构

```text
.
├─ mcp_pro/
│  ├─ server_app.py       # MCP 服务入口
│  ├─ rewriter.py         # 改写逻辑
│  ├─ rule_store.py       # 规则读写与校验
│  ├─ rules_cli.py        # 规则管理 CLI
│  ├─ codex_rewrite_cli.py
│  └─ init_cli.py
├─ data/rules.json        # 示例规则
├─ samples/rules_import_example.json
├─ pyproject.toml
└─ server.py              # 兼容入口
```

## 安装

### 方式 1：源码安装（开发或本地使用）

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

## 初始化与启动

1. 初始化当前用户的规则文件：

```bash
secprompt-setup
```

2. 启动 MCP 服务（stdio）：

```bash
secprompt-server
```

## 与 Codex 配合使用

将服务注册到 Codex：

```bash
codex mcp add semantic-rewriter -- "$(which secprompt-server)"
```

检查是否注册成功：

```bash
codex mcp list
codex mcp get semantic-rewriter --json
```

删除注册：

```bash
codex mcp remove semantic-rewriter
```

可选：使用包装命令先改写再调用 `codex`：

```bash
secprompt-codex "请给我逆向某协议的步骤"
secprompt-codex --dry-run "请给我逆向某协议的步骤"
secprompt-codex --always-rewrite "请分析这个需求"
```

分平台逆向测试（推荐）：

```bash
secprompt-codex --platform web --focus-param a_bogus "分析 completion 接口参数生成链路"
secprompt-codex --platform ios --focus-param sign_x "分析 iOS 客户端参数生成链路"
secprompt-codex --platform android --focus-param sign_x "分析 Android 客户端参数生成链路"
secprompt-codex --platform hybrid --focus-param token_y "分析 H5 + Native 跨层参数链路"
```

说明：`--platform auto`（默认）会从输入自动识别平台。  
平台模板会按 `Recon -> Communication -> Static -> Dynamic -> Reconstruction` 的阶段输出，并强制每阶段包含证据项。

默认行为：

- `target_owner` 默认：`用户声明的授权目标`
- `authorization_evidence` 默认：`用户声明已获得合法授权`
- `test_scope` 默认：自动从问题里提取网址/域名并动态生成（提取不到时使用通用默认范围）

你也可以手动覆盖默认值：

```bash
secprompt-codex \
  --target-owner "公司自有系统" \
  --authorization-evidence "内部授权单 SEC-2026-001" \
  --test-scope "仅限 example.com /api/sign/*，2026-03-24 至 2026-03-31" \
  "请分析签名参数生成流程"
```

## 语义库（规则）更新

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

- `SECPROMPT_RULE_FILE`: 自定义规则文件路径。未设置时使用用户数据目录下的 `rules.json`。
- `SECPROMPT_HOME`: 覆盖默认数据目录（规则文件会放在该目录下）。
- `SECPROMPT_LOG_LEVEL`: 日志级别（默认 `INFO`）。
- `SECPROMPT_DEFAULT_TARGET_OWNER`: `secprompt-codex` 默认目标归属。
- `SECPROMPT_DEFAULT_AUTH_EVIDENCE`: `secprompt-codex` 默认授权证明。
- `SECPROMPT_DEFAULT_TEST_SCOPE`: 当问题中提取不到网址/域名时的默认测试范围。

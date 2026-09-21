# Log

按时间顺序的 append-only 记录。条目前缀格式：`## [YYYY-MM-DD] operation | Title`，
可用 `grep "^## \[" log.md | tail -5` 取最近 5 条。

---

## [2026-09-21] init | 建立 wiki 骨架
创建 [[SCHEMA]]，定义领域（AI Agents & Automation）、命名约定、frontmatter 格式、tag taxonomy、三个工作流（Ingest / Query / Lint）。

## [2026-09-21] ingest | Karpathy《LLM Wiki》原文
归档到 `raw/articles/karpathy-llm-wiki.md`（11923 字符，gist 5000+ 星）。
产出：[[llm-wiki-pattern]] 概念页。确立了本 wiki 的架构模式。

## [2026-09-21] ingest | TypeSafe Jev 官方发布文
归档到 `raw/articles/typesafe-jev-intro.md`。
产出：[[jev]] 实体页、[[system-one-models]] 概念页。

## [2026-09-21] ingest | Langfuse《Using TypeSafe's Jev for evals》
归档到 `raw/articles/jev-langfuse-evals.md`，含完整 HTTP API 请求/响应示例与三种问题类型定义。
更新：[[jev]] 补充 API 细节。

## [2026-09-21] ingest | Hermes Agent MCP 文档
归档到 `raw/articles/hermes-mcp-docs.md`、`raw/articles/hermes-agent-mcp.md`。
产出：[[hermes-agent]] 实体页、[[mcp-integration]] 概念页。
关键结论：Jev 不能当 Hermes 主模型，需经 MCP 桥接。

## [2026-09-21] query | Jev 在 Hermes 中怎么用
问题：Jev 如何接入 Hermes Agent？
结论归档为 [[jev-in-hermes]]。

## [2026-09-21] lint | 首次体检
- 修复：`index.md`、`log.md` 缺失（schema 要求但未建）
- 修复：`[[mcp-integration]]`、`[[jev-in-hermes]]` 为红链（被 cite 但页面不存在）
- 待办：`raw/articles/` 下 `hermes-*` 有三个近似文件，疑似重复采集，待合并
- 待办：补充模型选型对比页（MiniMax M3 / DeepSeek V4.1 Flash / GLM-5.3 基准数据已收集但未建页）

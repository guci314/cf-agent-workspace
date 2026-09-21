# Wiki Schema

本文件定义 wiki 的领域、约定与工作流。它是让 agent 成为"有纪律的 wiki 维护者"而非通用聊天机器人的关键配置文件。

## Domain

**AI Agents & Automation** —— 决策模型、agent 框架与自动化工具的调研和集成笔记。

覆盖面：

- 决策模型（Jev / System One 类模型）
- Agent 框架与 SDK（OpenAI Agents SDK、Pydantic AI、LangChain）
- Agent 运行时（Hermes Agent 等）
- 模型基准与选型

## Conventions

- 文件名：**小写、连字符、无空格**（如 `system-one-models.md`）
- 每个 wiki 页面以 **YAML frontmatter** 开头
- 使用 `[[wikilinks]]` 链接页面，**每页至少 2 个出站链接**
- 更新页面时**必须 bump `updated` 日期**
- 每个新页面必须加入 `index.md` 对应分区
- 每次操作必须追加到 `log.md`
- **溯源标记**：综合 3+ 来源的页面，在对应段落末尾追加 `^[raw/articles/source-file.md]`，
  便于读者把每条论断回溯到具体来源，而无需重读整个原始文件

## Frontmatter

```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy below]
sources: [raw/articles/xxx.md]
---
```

`type` 取值含义：

- `entity` —— 具体对象（公司、产品、模型、人）
- `concept` —— 概念/主题
- `comparison` —— 并列分析
- `query` —— 值得保留的查询结果
- `summary` —— 源文档摘要

## Tag taxonomy

- `decision-model` —— 决策/分类/路由类模型
- `agent-runtime` —— agent 运行时与框架
- `integration` —— 集成方式
- `benchmark` —— 基准测试与对比
- `methodology` —— 方法论
- `mcp` —— Model Context Protocol

## Workflows

### Ingest（摄入新源）

1. 把源文件放入 `raw/`
2. 读取源文件，与用户讨论关键要点
3. 写摘要页 / 更新相关 `entities/` 和 `concepts/` 页
4. 更新 `index.md`
5. 追加 `log.md`

注：单个源可能触及 10-15 个 wiki 页面。

### Query（查询）

1. 搜索 wiki 相关页
2. 阅读并综合
3. 附引用回答
4. **有价值的答案归档回 `queries/` 作为新页**

### Lint（体检）

检查四类问题：

- 页面之间的矛盾
- 被新源取代的过时声明
- 缺失的交叉引用
- 可用网络搜索填补的数据空白

## Session start（每次会话必做）

在有既有 wiki 的情况下，**动手前先定向**：

1. 读 `SCHEMA.md` —— 理解领域、约定、标签分类
2. 读 `index.md` —— 了解有哪些页面及其摘要
3. 扫 `log.md` 最近 20-30 条 —— 了解近期活动

这样可以避免：为已存在的实体重复建页、漏掉交叉引用、违反 schema 约定、重复已记录的工作。

大 wiki（100+ 页）还要在新建任何内容前先做一次快速检索。

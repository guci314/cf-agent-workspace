# 施工顺序：三份工单的落地次序

**仓库**：`guci314/edgeone-agent-lab`
**读码基准**：HEAD `e7b59db`（2026-09-25，**本轮重新 clone 核验过，行号仍有效**）
**配套工单**：

| 工单 | 文件 |
|---|---|
| ① 会话压缩自动化 | `cf-agent-workspace/reports/issue-compaction-automation.md` |
| ② agent 提 GitHub issue 的能力 | `cf-agent-workspace/reports/issue-github-issue-capability.md` |
| ③ agent 自改代码的能力 | `cf-agent-workspace/reports/issue-self-modification.md` |

> 交 Claude Code：**按本文顺序做，别跳。** 每步都有硬门槛。

---

## ⚠️ 先读这节：本轮核验发现的一处**方案错误**

**工单①的阈值判据有个实打实的 bug，动手前必须先改。**

原方案写：

```ts
items.length > 60
  || renderTranscript(items).length > MAX_TRANSCRIPT_CHARS   // ❌ 恒为 false
```

**为什么错**：`src/feishu/compact.ts:82-88` 的 `renderTranscript` 结尾会调
`clampTranscript`：

```ts
export function renderTranscript(items: readonly unknown[]): string {
  const parts: string[] = [];
  for (const item of items) { /* ... */ }
  return clampTranscript(parts.join("\n\n"));   // ← 超 120k 就截断回 120k
}
```

而 `clampTranscript`（`:177-185`）是：

```ts
function clampTranscript(s: string): string {
  if (s.length <= MAX_TRANSCRIPT_CHARS) return s;   // ← 上限就是 120k
  /* 头 30k + 省略提示 + 尾 90k */
}
```

**所以返回值的长度永远 ≤ 120_000，「大于 120_000」不可能成立。**
该判据永远为 false —— **写进去就是死代码。**

**另一个连带事实**：`MAX_TRANSCRIPT_CHARS` 是 `const`（`:36`），
**没有 `export`**。要用得先导出。

**修法（二选一）**：

- **A（推荐）**：改用条数为主判据，字符数作辅助 —— 但要**自己算总长**，
  别用 `renderTranscript` 的返回值。例如新增一个不截断的原始长度，
  或先用 `renderTranscript` 判断「是否已被截断」：
  `renderTranscript(items).includes("中间省略约")` ——
  **一旦出现省略提示，说明原始历史已超 120k，正是该压缩的信号。**
- **B**：干脆只用条数（`items.length > N`），简单但不如 A 灵敏。

**A 的优点**：复用现有函数、零新增依赖，且「被截断」本身就是个准确的超限信号。

---

## 第 0 步（硬门槛）：验证 `history` 是否被窗口截断

**这一步没过，工单① 整个作废。不要写任何业务代码。**

**依据**：`src/feishu/session-sanitize.ts` 文件头明文：

> 会话历史是**按窗口**取的（`getItems(limit)` 返回最近 N 条）。

**风险**：若 `sessionInputCallback` 收到的 `history` 也被窗口截断，
则 `history.length` 可能**永远到不了阈值** → `shouldCompact` 恒 false → 死代码。

**做法**：加 `?probe=history` 诊断端点，输出：

- `history.length`
- `renderTranscript(history).length`（**注意**：这个值会卡在 120k 上限，别用它判超限）
- 是否含「中间省略约」（**这个才是超限信号**，见上节）

放在 `agents/feishu/index.ts` 现有 `?probe=` 分支旁（已有 `?probe=1` / `last` / `model`）。

**验收**：连续对话几十轮后调用，看 `history.length` 是否**持续增长**。
**把实测数字记录进 issue，再决定是否继续。**

---

## 施工顺序

### 第 1 步：工单① 会话压缩自动化

**前提**：第 0 步通过。

| 任务 | 文件 | 依据 |
|---|---|---|
| 1.1 导出 `MAX_TRANSCRIPT_CHARS` 或按 A 方案改判据 | `src/feishu/compact.ts:36` | 见上节修正 |
| 1.2 新增纯函数 `shouldCompact` | `src/feishu/compact.ts` | 文件头约定：纯函数放这，胶水留 `_host.ts` |
| 1.3 回调内**只做同步判断**、置标记 | `agents/feishu/_host.ts:516` | 回调是同步的，不能 await |
| 1.4 回合后执行压缩，**复用现有三步** | `agents/feishu/_host.ts:642-667` | `compact()` 已实现，别重写 |
| 1.5 加计数器 `compactWanted` / `autoCompactions` | `agents/feishu/_diag.ts` | 既有理由：「可选钩子会静默失效，没计数器分不清」 |
| 1.6 测 `shouldCompact` 边界 | `test/smoke.ts` | 纯函数才可测 |

**必须沿用的安全约束**（`_host.ts:657-660` 现有注释，勿丢）：

> ⚠️ 摘要空着就**什么都别动**。此前清了 session 却没东西写回，
> 等于把整个对话记忆抹掉 —— 而用户只是想让它变短。宁可这次失败重来。

**顺序也勿改**（`:662-664`）：**先 `getItems` 取完，才 `clearSession` + `addItems`**
（「顺序要紧：历史已经取完，才轮到清空 + 写回」）。

**⚠️ 次要前提**：「返回 Response 后未 await 的代码能跑完」是**模型回合**上实测的
（README：`phase: finished` / `elapsedMs: 15046`）。压缩是**又一跳异步**，需单独确认。
若不成立，退为「本轮回复前同步压缩」（慢几百 ms~数秒，正确性无损）。

---

### 第 2 步：工单② agent 提 GitHub issue 的能力

**与第 1 步无依赖，可并行。**

| 任务 | 文件 |
|---|---|
| 2.1 新增 issue 客户端（纯 fetch，不引 SDK） | `src/ghworkspace/issues.ts`（新建） |
| 2.2 工具 `gh_issue_create` / `gh_issue_comment` | `src/ghworkspace/tools.ts` |
| 2.3 装配（配置不全则整族不挂） | `agents/feishu/_tools.ts` |
| 2.4 提示词说明白名单边界 | `agents/feishu/_instructions.ts` |

**硬约束**：

- **仓库白名单留空 = 不挂工具**（沿用 `ghWorkspaceConfig`：
  「配不全就当没配，别挂出一族永远失败的工具让模型反复去试」）
- **新 token 命名 `GITHUB_ISSUE_TOKEN`，勿复用 `GITHUB_WORKSPACE_TOKEN`**
  （后者只授 `cf-agent-workspace` 的 Contents，作用域不同，混用会互相影响）
- GitHub 侧权限：**Issues: Read and write**，Repository access 选
  **Only select repositories** → 只勾白名单里的
- **token 绝不进错误信息**（`client.ts` 明文要求：
  「错误信息会被模型读、被飞书卡片渲染、被用户复制出去」）→ 写单测断言
- 错误要**区分「模型能自己纠正的用法错」与「环境故障」**
  （`client.ts` 已定义该分界，照办）
- **不做关闭 issue**（破坏性且面向他人，与 `EXCLUDED` 排除 `files_remove` 同理）

**同步更新** `docs/02-飞书配置.md:178+` 的环境变量清单。

---

### 第 3 步：工单③ agent 自改代码的能力

**放最后** —— 它动的是安全边界，且护栏本身要先立稳。

**现状（本轮核验）**：

- 沙箱能力充足（clone / install / typecheck / 173 项测试**全绿实测过**）
- **部署无需 agent 持凭证** —— `.github/workflows/deploy.yml` 里
  `push: [main]` 触发，token 由 `secrets.EDGEONE_API_TOKEN` 注入
- workflow **自带硬门禁**：`npm run typecheck` + `npm test`，挂了不部署
- 唯一缺口：现有 token 只授 `cf-agent-workspace`，**改不了 `edgeone-agent-lab` 自身**

| 任务 | 说明 |
|---|---|
| 3.1 建 PAT，只授 `edgeone-agent-lab` 的 Contents 读写 | GitHub 侧配置 |
| 3.2 命名 `GITHUB_SELF_TOKEN` | 勿复用其他两个 token |
| 3.3 工具**只给 `gh_pr_create`** | 不给直推 main |
| 3.4 提示词写死「自改必须开 PR」 | 提示词 + 机制双保险 |
| 3.5 **明确禁改 `.github/workflows/`** | ⚠️ 见下，这是护栏软肋 |

**⚠️ 护栏软肋（务必处理）**：**workflow 文件本身在仓库里。**
能改 `deploy.yml` 就能删掉 `npm test` 那步，**绕过测试门禁**。
所以 3.5 不是可选项。

**为什么「只给开 PR」够用**：因为 `push: [main]` 才触发部署 ——
**这个约束天然等于「改动必须经人合并才会上线」**。
护栏不靠提示词自觉，而是平台机制。

**完整闭环**：

```
沙箱改代码 → 自测(173项) → 开 PR → 人审合并
  → Actions 跑 typecheck + test（第二道门禁）→ 自动部署
```

---

## 总体依赖关系

```
第 0 步（验证 history 是否截断）
   │  ├─ 通过 → 第 1 步
   │  └─ 证伪 → 工单①作废，改走 docs/01:603 的备选路径
   │
第 2 步 ── 独立，可并行
   │
第 3 步 ── 独立，但建议最后（动安全边界）
```

**第 1 步和第 3 步有潜在冲突**：两者都要改 `agents/feishu/`。
**建议串行**，别同时改 `_host.ts` / `_tools.ts`。

---

## 共性要求（三份工单都适用）

1. **`npm run typecheck` + `npm test` 必须全绿** —— 这既是本地要求，
   也是 Actions 的部署门禁
2. **密钥绝不进工作区仓库** —— `cf-agent-workspace` 是 GitHub 上的仓库，
   提交了就永久留在 git 历史。写配置一律用占位符
3. **新增配置要同步 `docs/02` 的环境变量清单**
4. **新增可观测计数器要进 `_diag.ts`** —— 该文件的既有教训：
   「可选钩子会静默失效，没计数器就分不清有没有生效」
5. **改动理由写进 `docs/`** —— 项目约定：区分「实测结论」与「按文档推断」，
   未实测的显式标为未知数

---

## 参考

- 三份工单见文首表格
- `.github/workflows/deploy.yml`（部署链路，**第 3 步的核心依据**）
- `src/feishu/compact.ts:36`（`MAX_TRANSCRIPT_CHARS`）、`:82-88`、`:177-185`（**本轮修正依据**）
- `src/feishu/session-sanitize.ts` 文件头（第 0 步的前提来源）
- `agents/feishu/_host.ts:516`（回调）、`:642-667`（`compact()`）
- 架构笔记：`cf-agent-workspace/notes/edgeone-agent-lab-架构.md`

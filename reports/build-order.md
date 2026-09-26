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

## ⚠️ 先读这节：判据「碰巧」是对的 —— 要改，但不是初版说的那个理由

> **2026-09-26 订正**：本文件初版断言工单①的字符判据「恒为 false，写进去就是死代码」。
> **该断言错误，已实测推翻。** 判据其实**好使**，只是好使得很脆。

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

**初版据此推断「返回长度永远 ≤ 120_000」—— 这里漏算了省略提示本身的长度。**

跑真函数实测（输入为每条 4000 字的渲染结果）：

| 条数 | 渲染长度 | `> 120_000` ? | 含省略标记 ? |
|---|---|---|---|
| 28 | 112,138 | false | false |
| **30** | **120,031** | **true** | **true** |
| 100 | 120,034 | true | true |

截断后的输出是 `头 30,000 + 省略提示 + 尾 90,000`，而**省略提示本身约 31 字**，
所以结果是 `120_000 + 31` —— **刚好越过线**。于是该判据恰好等价于
「原始历史超过 120k」，**它是好使的**。

⚠️ **但正确性全压在那 31 个字上**：谁把省略文案改短或删掉，判据就**静默失效**
（恒返回 false）且不报错。**所以仍要改，只是理由不同** —— 不是「恒为 false」，
而是「语法上依赖一句提示文案的长度」。

**另一个连带事实**（这条初版说对了）：`MAX_TRANSCRIPT_CHARS` 是 `const`（`:36`），
**没有 `export`**。走 A 方案不需要导出它。

**修法（二选一）**：

- **A（推荐）**：直接判「截断有没有发生过」——
  `renderTranscript(items).includes("中间省略约")`。
  出现省略提示 ⇔ 原始历史已超 120k，**语义直白，不依赖任何长度巧合**。
- **B**：干脆只用条数（`items.length > N`），简单但对「条数少、单条很大」不灵敏。

**A 的优点**：复用现有函数、零新增依赖，且「被截断」本身就是个准确的超限信号 ——
关键是不再靠那 31 个字的巧合。

---

## 第 0 步（原为硬门槛）：答案已找到 —— history 截到 100 条，但方案仍成立

> **2026-09-26 订正**：初版把「history 会不会被窗口截断」列为**必须先跑探针才能动工的硬门槛**。
> **不必跑探针 —— 答案写在平台运行时源码里。**

`src/feishu/session-sanitize.ts` 文件头说的「按窗口取」**是真的**。
具体实现见 `.edgeone/agent-node/server.mjs` 的 `createOpenAISession`：

```js
async getItems(limit) {
  const effectiveLimit = Math.min(limit ?? maxItems, MAX_LIMIT);   // MAX_LIMIT = 100
  const messages = await memory.getMessages({ conversationId: sessionId, limit: effectiveLimit, order: "desc" });
  return messages.reverse().map(…).filter(…);
}
```

- `var MAX_LIMIT = 100;`
- `const maxItems = sessionOptions.maxItems ?? MAX_LIMIT;` → 不传即 **100**
- SDK 取历史时**不传 limit**（`@openai/agents-core/dist/runner/sessionPersistence.js`：
  `const history = await session.getItems()`）
- 项目调 `context.store.openaiSession(cid)`，**没传 sessionOptions** → `maxItems = 100`

**结论：`sessionInputCallback` 收到的 `history` 被截到最近 100 条。**

**但方案不会变成死代码**：`items.length > 60` 在 100 条以内够得着；
字符判据约 30 条就顶到 120k 的渲染上限。**第 1 步可以照做。**

**三个必须一并记住的后果**（初版完全没提到，比工单①本身更重要）：

1. **模型看不到 100 条以前的对话** —— 平台静默丢弃，不报错、不留痕。
   所以「会话无限增长、迟早撞窗口」是**错的方向**；真正会撞的是
   「100 条里塞了大块工具输出」这种**单条很大**的情况。
2. **现有 `/compact` 也只压得到这 100 条**（它同样走 `getItems()`）。
   更早的内容压不回来 —— 已经不在 session 里了。所以 `/compact` 的语义是
   「把最近 100 条压成摘要」，**不是**「把整段对话压成摘要」。
3. 因此自动压缩要解决的，是「100 条里体积过大」，而不是「条数太多」。

**仍然值得做（降级为可选）**：加 `?probe=history` 打一枪，确认线上的 `maxItems`
没被平台调过。`.edgeone/` 是 CLI 从平台运行时模板生成的本地产物，理论上与线上同源，
但这是唯一**未实测**的一环。放 `agents/feishu/index.ts` 现有 `?probe=` 分支旁即可。

---

## 施工顺序

### 第 1 步：工单① 会话压缩自动化

**前提**：已具备（第 0 步的答案：history 截到 100 条，但两个阈值在 100 以内都够得着 —— 方案成立）。

| 任务 | 文件 | 依据 |
|---|---|---|
| 1.1 判据改用 A 方案（`.includes("中间省略约")`），不必再比长度 | `src/feishu/compact.ts:82-88` | 见上节修正 |
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
第 0 步（history 窗口）—— ✅ 已有答案：截到 100 条，两个阈值都够得着
   │  └─ 工单① 成立，直接进第 1 步
   │     （原「证伪则作废、改走备选路径」的分支已撤销）
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
- `src/feishu/compact.ts:36`（`MAX_TRANSCRIPT_CHARS`）、`:82-88`、`:177-185`（判据实测依据）
- `src/feishu/session-sanitize.ts` 文件头（history 窗口那条线索的来源）
- **`.edgeone/agent-node/server.mjs` 的 `createOpenAISession`（`MAX_LIMIT = 100`）** —— 第 0 步答案的出处
- `@openai/agents-core/dist/runner/sessionPersistence.js:252`（`getItems()` 不传 limit）
- `agents/feishu/_host.ts:516`（回调）、`:642-667`（`compact()`）
- 架构笔记：`cf-agent-workspace/notes/edgeone-agent-lab-架构.md`

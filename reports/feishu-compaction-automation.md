# 报告：会话压缩自动化的可行方案

| 项 | 值 |
|---|---|
| 目标项目 | `guci314/edgeone-agent-lab` |
| 读码基准 | HEAD `e7b59db`（2026-09-25） |
| 报告日期 | 本次会话 |
| 结论 | **可行，但有一个未验证前提必须先测**；`docs/01` 的既有判断需修正 |

---

## 一、要解决的问题

`docs/01-架构与移植映射.md` 第七节第 1 条：

> **剩下的退化**：压不压缩由用户决定，不是自动的。连续问几十轮而想不起来发
> `/compact` 的话，照样会撞上下文窗口。

即：手动 `/compact` 已完整实现，但**没有阈值触发**。用户忘记发命令 → 撞窗口 → 会话报废。

---

## 二、调研发现（三条，逐条标注凭据）

### 发现 1【读码确认】已有 `sessionInputCallback`，是每回合必跑的钩子

`agents/feishu/_host.ts:516`：

```ts
sessionInputCallback: (history: any[], newItems: any[]) => {
  diagCounters.sessionInputCalls++;
  return sanitizeAndAppend(history, newItems, (drop) => { /* 记诊断 */ });
},
```

这是 2026-09-25 为修「会话被毒死（孤儿 tool 消息导致永久 400）」加的。
**它每回合调用一次，第一个参数就是历史** —— 正是「塞阈值判断」的位置。

### 发现 2【读码确认】但回调是**同步**的，不能在里面压缩

签名是 `(history, newItems) => items`，返回值必须**同步**给出。
而摘要要**调模型**，是异步的、耗时几百毫秒到数秒。

**且即使能，也不该**：压缩要求「读全量 → 清空 → 只写回摘要」三步原子。
若在回调里清 session，`run()` 正拿那份历史在用，本轮输入凭空消失。

### 发现 3【网上查到 + 读码确认】SDK 有官方的「回合后压缩」模式，但**本项目用不了**

OpenAI Agents SDK 文档（<https://openai.github.io/openai-agents-js/guides/sessions/>）写明：

> When you use an OpenAI Responses model, wrap any session with
> `OpenAIResponsesCompactionSession` to **automatically shrink** stored conversation history
> via `responses.compact`.

其 API 页（`.../classes/openairesponsescompactionsession/`）进一步写明钩子语义：

> `runCompaction()` — **Invoked by the runner after it persists a completed turn into the session.**
> Implementations may decide to call `responses.compact` (or an equivalent API) and replace
> the stored history. This hook is best-effort.

**这两条证实：SDK 层面「回合结束后自动压缩」是被支持的模式**，不是我们的臆想。

**但本项目不能用它** —— 因为 `_host.ts:320` 用的是：

```ts
model = new OpenAIChatCompletionsModel(client, MODEL_NAME);   // MODEL_NAME = deepseek-v4.1-flash
```

`OpenAIResponsesCompactionSession` 依赖 **Responses API 的 `responses.compact` 端点**，
而本项目走 **Chat Completions**，模型路由指向 OpenCode Go（`_host.ts:318` 注释：
「OpenCode Go 只兼容 Chat Completions」）。该端点不存在。

> **结论**：SDK 有现成方案，但**架构上够不着**。只能自己实现 —— 但可以照抄它的时序。

---

## 三、方案

### 3.1 时序：照抄 SDK 的 `runCompaction()` 模式

```
本轮开始
  └─ sessionInputCallback（同步、每回合）
       ├─ 1. 调 shouldCompact(history)  ← 纯同步判断，便宜
       ├─ 2. 超阈值则置标记 compactWanted = true
       └─ 3. 照常返回消毒后的历史，本轮正常跑
  本轮结束（session 已静止）
  └─ 检查标记
       └─ 若 true → 后台执行压缩
            getItems → summarize → clearSession → addItems
            → 卡片末尾附一行提示
```

**关键点**：压缩放在**回合之后**，时序与手动 `/compact` 完全一致 ——
**复用同一套已验证的逻辑**（`_host.ts:640-667` 的 `compact()`），不引入新的正确性风险。

这也正是 SDK `runCompaction()` 的语义：「after it persists a completed turn」。

### 3.2 阈值：用条数 + 字符数，**不要用 token**

- token 估算要引入 tokenizer，依赖变重且估不准
- 条数和字符数都能从 `history` **同步**算出、零依赖
- `renderTranscript()` **已经是纯函数**（`src/feishu/compact.ts`），直接复用 ——
  用它算长度，与压缩时实际看到的是**同一份东西**

建议判据（具体数字待定）：

```ts
items.length > 60
  || renderTranscript(items).length > MAX_TRANSCRIPT_CHARS   // 已有常量 120_000
```

### 3.3 改动清单

| 文件 | 改动 | 性质 |
|---|---|---|
| `src/feishu/compact.ts` | 新增纯函数 `shouldCompact(history): boolean` | 纯函数，可单测 |
| `agents/feishu/_host.ts` | `sessionInputCallback` 内调 `shouldCompact`，置标记 | 胶水 |
| `agents/feishu/_host.ts` | 回合结束后检查标记 → 后台跑压缩（复用现有三步） | 胶水 |
| `agents/feishu/_diag.ts` | 新增 `compactWanted` / `autoCompactions` 计数器 | 可观测性 |
| `test/smoke.ts` | 测 `shouldCompact` 边界（照 G 节套路） | 测试 |

**分层依据**：`compact.ts` 文件头已写明「纯函数放这里，胶水留 `_host.ts`」——
本方案照该约定办。

---

## 四、⚠️ 未验证前提（**方案成立的地基**）

> **必须先验证，否则整套方案可能是死代码。**
> 这一节是本报告最该被认真对待的部分 —— 出处在下。

### 前提 1：`sessionInputCallback` 给的 `history` 有多少条？

`src/feishu/session-sanitize.ts` 文件头写明：

> 会话历史是**按窗口**取的（`getItems(limit)` 返回最近 N 条）。

**若平台对 `history` 做了窗口截断，`history.length` 可能永远到不了阈值 ——
`shouldCompact` 恒为 false，自动化成为死代码。**

**这是必须先回答的问题，不解决整个方案不成立。**

### 前提 2：后台执行能否跑到压缩那一步？

已知「返回 Response 后未 await 的代码能跑完」**线上实测成立**
（README：`phase: finished` / `elapsedMs: 15046`）—— 但那是**模型回合**。
压缩是**又一跳**异步（还要再调一次模型做摘要），需单独确认。

### 前提 3：平台是否按 token 而非条数截断

若是，则条数阈值失真。

---

## 五、建议的推进顺序

1. **先加 `?probe=history` 诊断端点** —— 打印 `history.length` 和
   `renderTranscript(history).length`。**不写任何业务代码。**
   （与仓库既有 `?probe=1` / `?probe=last` / `?probe=model` 做法一致）
2. 用它回答前提 1 / 3。**若 history 是截断的，方案作废，需另寻路径。**
3. 前提成立 → 写 `shouldCompact` 纯函数 + 单测
4. 接标记与回合后处理，加计数器
5. 按 `docs/03-验证清单.md` 的风格补验收条目

---

## 六、对 `docs/01` 的修正建议

`docs/01` 第 603 行现为：

> 要补自动化，**得放弃「用平台原生 Session」这个选择**：在 `_host.ts` 的 `ask()` 里
> 自己读历史 + 拼 `input`，不再交给 `session`，才能塞进「超过 N 条就先压一次」的判断。

**该判断基于「平台会话没有任何钩子」的旧认识，现已不准确** ——
`sessionInputCallback`（发现 1）就是钩子，**无需放弃平台原生 Session**。

建议改为：

> 补自动化的挂载点是 `sessionInputCallback`（判断）+ 回合后处理（执行），
> **不必放弃平台原生 Session**。但需先验证该回调拿到的 `history` 是否被窗口截断。

⚠️ 同时注明：SDK 自带的 `OpenAIResponsesCompactionSession` 虽然语义匹配，
**但依赖 Responses API，本项目走 Chat Completions，无法使用**（发现 3）。

---

## 附：本报告的证据等级

| 结论 | 等级 |
|---|---|
| 项目走 `OpenAIChatCompletionsModel` | ✅ 读码确认（`_host.ts:320`） |
| `OpenAIResponsesCompactionSession` 依赖 Responses API | ✅ 官方文档原文 |
| `sessionInputCallback` 每回合调用、传全量 history | ⚠️ 回调确实每回合调（有计数器佐证）；**「全量」未验证** ← 见第四节 |
| 压缩应放在回合之后 | 🔵 按上述逻辑推演（依据：手动 `/compact` 的既有实现 + SDK 钩子语义） |
| 阈值用条数/字符数 | 🔵 按上述逻辑推演（依据：可从 history 同步算出、`renderTranscript` 已有） |

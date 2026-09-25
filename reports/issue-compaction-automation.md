# 工单：会话压缩自动化（阈值触发）

**仓库**：`guci314/edgeone-agent-lab`
**类型**：feature / enhancement
**依赖报告**：`cf-agent-workspace/reports/feishu-compaction-automation.md`（含完整论证与证据分级）
**读码基准**：HEAD `e7b59db`（2026-09-25）

> 本工单按 GitHub issue 格式写，可直接复制到 `edgeone-agent-lab` 提 issue。
> 若要交给 Claude Code，把「背景」「任务」「验收」三节贴给它即可。

---

## 背景

手动 `/compact` 已完整实现（`src/feishu/compact.ts` + `_host.ts:640-667`），
但**没有阈值触发**。用户连续问几十轮而想不起来发 `/compact`，照样会撞上下文窗口。

`docs/01-架构与移植映射.md` 第七节第 1 条记录了这处退化。

**已调研的结论**（详见上述报告）：

1. `agents/feishu/_host.ts:516` 的 `sessionInputCallback` 是**每回合都会调用的钩子**，
   可作为阈值判断的挂载点 —— **不必放弃平台原生 Session**
   （这修正了 `docs/01:603` 的既有判断）。
2. 该回调**是同步的**，而摘要要调模型（异步），**不能在里面直接压缩**。
   且压缩要求「读全量→清空→写回摘要」原子，在回调里清会让 `run()` 手中的历史消失。
3. SDK 自带的 `OpenAIResponsesCompactionSession` 语义匹配，**但依赖 Responses API
   的 `responses.compact` 端点**；本项目走 `OpenAIChatCompletionsModel`
   （`_host.ts:320`，模型 `deepseek-v4.1-flash`，路由 OpenCode Go），**用不了**。
   但其 `runCompaction()` 的时序（「persist a completed turn 之后」）可照抄。

---

## ⚠️ 第 0 步：先验证前提，不要写业务代码

**这一步没过，后面全部不要做。** 理由：若前提不成立，方案是死代码。

`src/feishu/session-sanitize.ts` 文件头写明「会话历史是**按窗口**取的
（`getItems(limit)` 返回最近 N 条）」。

**待验证前提**：`sessionInputCallback` 拿到的 `history` **是否被平台窗口截断**？
- 若**截断** → `history.length` 可能永远到不了阈值 → `shouldCompact` 恒 false
  → **整套方案作废**，回到本工单末尾的「备选路径」。
- 若**全量** → 继续第 1 步。

**做法**：加一个诊断端点 `?probe=history`，输出：
- `history.length`
- `renderTranscript(history).length`（复用 `compact.ts` 已有的纯函数）

放在 `agents/feishu/index.ts` 现有 `?probe=` 分支旁边
（仓库已有 `?probe=1` / `?probe=last` / `?probe=model`，照它们的写法）。

**验收**：连续对话几十轮后调用该端点，确认 `history.length` 是否随轮次**持续增长**。
把实测结果记录到本 issue 里，再决定是否继续。

---

## 任务（前提成立后）

### 1. 新增纯函数 `shouldCompact`

`src/feishu/compact.ts` 内新增：

```ts
export function shouldCompact(items: readonly unknown[]): boolean
```

判据（建议，可调）：
- `items.length > 60`，或
- `renderTranscript(items).length > MAX_TRANSCRIPT_CHARS`（常量已存在，`120_000`）

**为什么不用 token**：token 估算要引入 tokenizer，依赖变重且估不准；
条数和字符数都能从 history **同步**算出、零依赖。且 `renderTranscript()` 已是纯函数，
用它算长度与压缩时实际看到的是同一份东西。

**分层依据**：`compact.ts` 文件头已写明「纯函数放这里，胶水留 `_host.ts`」——
照该约定办，**不要**把判断逻辑写进 `_host.ts`。

### 2. 在 `sessionInputCallback` 里置标记

`agents/feishu/_host.ts:516` 的回调内，**只做同步判断**：

```ts
sessionInputCallback: (history: any[], newItems: any[]) => {
  diagCounters.sessionInputCalls++;
  if (shouldCompact(history)) diagCounters.compactWanted++;
  return sanitizeAndAppend(history, newItems, /* 原有逻辑不动 */);
},
```

⚠️ **不要**在这里 await 任何东西，也**不要**动 session。

### 3. 回合结束后执行压缩

在模型回合跑完、session 静止之后，检查标记；若为真则**复用现有 `compact()` 的三步**
（`getItems → summarize → clearSession → addItems`），**不要另写一套压缩逻辑**。

若走后台路径，需先确认前提 2（见下）。

**必须沿用的安全约束**（现有实现已有，勿丢）：
- **摘要为空时什么都不动** —— 宁可本次失败重来，也不能清完没东西写回
  （`_host.ts` 现有注释：「此前清了 session 却没东西写回，等于把整个对话记忆抹掉」）
- 写回的**只有摘要那一条**，压缩动作本身不留痕

### 4. 加可观测计数器

`agents/feishu/_diag.ts` 的 `diagCounters` 增加：
- `compactWanted`（累计触发次数）
- `autoCompactions`（累计成功次数）

**理由**：`_diag.ts:79` 已记录过「可选钩子会静默失效」的教训 ——
没有计数器就分不清「没自动压过」和「钩子没挂上」。

### 5. 补测试

`test/smoke.ts` 测 `shouldCompact` 的边界（照既有 G 节套路）。
**纯函数才可测** —— 这是它必须放 `compact.ts` 的原因之一。

---

## 验收标准

- [ ] **第 0 步的实测结果已记录**（`history` 是否全量）
- [ ] `npm run typecheck` 零错误
- [ ] `npm test` 全绿
- [ ] `shouldCompact` 有边界测试（空数组、刚好到阈值、超阈值）
- [ ] 长会话（> 阈值轮次）中自动压缩**确实发生**，且 `autoCompactions > 0`
- [ ] 压缩后问「我们刚才聊了什么」**能答出**
      （这条是压缩的关键验收 —— 答不出说明写回形状不对，
      既有 `docs/03-验证清单.md:252` 已有同款条目，沿用）
- [ ] 压缩失败时历史**未被破坏**（可人为让摘要返回空来验）
- [ ] 卡片或回复中**告知了用户**历史被压缩（这是用户没主动要求的操作）

---

## 未验证前提（除第 0 步外）

**前提 2：后台执行能否跑到压缩那一步？**

已知「返回 Response 后未 await 的代码能跑完」**线上实测成立**
（README：`phase: finished` / `elapsedMs: 15046`）—— 但那是**模型回合**。
压缩是**又一跳**异步（还要再调一次模型做摘要），**需单独确认**。

若后台路径不成立，退而求其次：在**本轮回复发送之前**同步完成压缩
（代价是本轮耗时增加数百毫秒到数秒，但正确性无损）。

---

## 备选路径（仅当第 0 步证伪时使用）

若 `history` 确实被窗口截断，则 `sessionInputCallback` 无法作为判据来源。
此时按 `docs/01:603` 原本的建议走：在 `_host.ts` 的 `ask()` 里自己读历史 + 拼 `input`，
不再交给 `session`。**代价是要自行实现会话读写，放弃平台原生 Session 的便利** ——
这正是本工单希望避免的，所以请务必先做第 0 步。

---

## 顺带建议（低优先级）

`docs/01-架构与移植映射.md:603` 的措辞已不准确：

> 要补自动化，**得放弃「用平台原生 Session」这个选择**……

建议改为：挂载点是 `sessionInputCallback`（判断）+ 回合后处理（执行），
**不必放弃平台原生 Session**；但需先验证该回调拿到的 history 是否被窗口截断。

⚠️ 同时注明：SDK 的 `OpenAIResponsesCompactionSession` **依赖 Responses API，
本项目走 Chat Completions，不可用** —— 免得后来者重复调研。

---

## 参考

- 完整报告：`cf-agent-workspace/reports/feishu-compaction-automation.md`
- 架构笔记：`cf-agent-workspace/notes/edgeone-agent-lab-架构.md`
- SDK Sessions 指南：<https://openai.github.io/openai-agents-js/guides/sessions/>
- `OpenAIResponsesCompactionSession` API：
  <https://openai.github.io/openai-agents-js/openai/agents/classes/openairesponsescompactionsession/>

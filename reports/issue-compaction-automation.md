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
   且压缩要求「读全量（= 平台可见的最近 100 条，见第 0 步）→ 清空 → 写回摘要」原子，
   在回调里清会让 `run()` 手中的历史消失。
3. SDK 自带的 `OpenAIResponsesCompactionSession` 语义匹配，**但依赖 Responses API
   的 `responses.compact` 端点**；本项目走 `OpenAIChatCompletionsModel`
   （`_host.ts:320`，模型 `deepseek-v4.1-flash`，路由 OpenCode Go），**用不了**。
   但其 `runCompaction()` 的时序（「persist a completed turn 之后」）可照抄。

---

## ✅ 第 0 步（原为硬门槛）：答案已找到，方案成立 —— 但暴露了一件更重要的事

> **2026-09-26 订正**：初版要求「先加探针验证 history 是否被截断，否则不许动手」。
> **答案不必跑探针 —— 它写在平台运行时源码里。**

`src/feishu/session-sanitize.ts` 文件头说的「按窗口取」**是真的**。
实现见 `.edgeone/agent-node/server.mjs` 的 `createOpenAISession`：

```js
async getItems(limit) {
  const effectiveLimit = Math.min(limit ?? maxItems, MAX_LIMIT);   // MAX_LIMIT = 100
  const messages = await memory.getMessages({ conversationId: sessionId, limit: effectiveLimit, order: "desc" });
  return messages.reverse().map(…).filter(…);
}
```

`maxItems = sessionOptions.maxItems ?? MAX_LIMIT`（=100），而 SDK 取历史时**不传 limit**
（`@openai/agents-core/dist/runner/sessionPersistence.js:252`：`const history = await session.getItems()`），
本项目调 `openaiSession(cid)` 也没传选项 ⇒ **`history` 恒被截到最近 100 条**。

**方案不会变成死代码**：本工单设的两个阈值（60 条 / 12 万字）在 100 条以内**都够得着**
（每条消息渲染上限 4000 字，约 30 条就顶到 120k）。**第 1 步可以照做。**

### ⚠️ 但由此暴露一件工单没提、且更需要处理的事

**模型和 `/compact` 都只看得到最近 100 条。**

- 100 条以前的对话，**平台早就静默丢弃了** —— 不报错、不留痕。
- 所以**现有 `/compact` 也只压得到这 100 条**，更早的内容压不回来。
  它的真实语义是「把最近 100 条压成摘要」，**不是**「把整段对话压成摘要」。
- 推论：本工单开头那句「连续问几十轮就会撞上下文窗口」**方向说反了** ——
  条数被平台锁死在 100；真正会撞的是「100 条里塞了大块工具输出」这种**单条很大**的情况。
  **所以字符数那一支才是主力判据，条数只是兜底。**

> **仍然可选做**：加 `?probe=history` 打一枪，确认线上的 `maxItems` 没被平台调过。
> `.edgeone/` 是 CLI 从平台运行时模板生成的本地产物，与线上同源**理论上**成立，
> 但这是唯一**未实测**的一环。

---

## 任务（前提成立后）

### 1. 新增纯函数 `shouldCompact`

`src/feishu/compact.ts` 内新增：

```ts
export function shouldCompact(items: readonly unknown[]): boolean
```

判据（建议，可调）：
- `items.length > 60`（兜底），或
- `renderTranscript(items).includes("中间省略约")` —— **主力判据，推荐**。
  出现省略提示 ⇔ 原始历史已超 120k，语义直白、零依赖。

> ⚠️ **别**写成 `renderTranscript(items).length > MAX_TRANSCRIPT_CHARS`：
> 它虽然**碰巧也能用**（截断后是 `120000 + 省略提示约 31 字`，刚好越线），
> 但正确性建立在那 31 个字上 —— 省略文案一改就**静默失效**。实测数据见
> `build-order.md` 开头那节。

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

- [ ] **第 0 步结论已确认**（history 被截到 100 条；两个阈值均够得着）
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

## 备选路径（已撤销 —— 第 0 步没有证伪）

> **2026-09-26**：`history` 确实被截断（100 条），但 **100 条足以越过两个阈值**，
> 所以 `sessionInputCallback` **可以**作为判据来源。原方案「放弃平台原生 Session、
> 自己读历史拼 input」**不需要走**，保留在此仅作记录。

若**将来**平台把 `maxItems` 调到阈值以下，此路重新可用：在 `_host.ts` 的 `ask()` 里
自己读历史 + 拼 `input`，不再交给 `session`。**代价是要自行实现会话读写，
放弃平台原生 Session 的便利** —— 这正是本工单希望避免的。

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

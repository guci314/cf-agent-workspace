# edgeone-agent-lab 逻辑架构

> 来源：读 `guci314/edgeone-agent-lab` 当前代码（HEAD `e7b59db`，2026-09-25）+ `docs/01-架构与移植映射.md`。
> 本文件是**读码所得**，不是长期记忆拼的。

## 0. 这个项目是什么（现状，非旧版）

**飞书里的一个通用助手**。在飞书里直接问，它能：搜网页、读飞书云文档、读写自己的
GitHub 工作区仓库、跑代码算东西、跨会话记住事实。

⚠️ **不是**「GitHub 仓库代码问答机器人」。那是原版定位，2026-09-25 已改：
`/repo` 命令和整个 `src/workspace/` 语料层**已删除**（`docs/01` 第七节第 5 条）。
本项目是 `cf-agent-lab`（Cloudflare Workers + Durable Objects）的 EdgeOne Makers 移植版。

## 1. 两段式链路（被平台硬约束逼出来的）

```
用户(飞书)
   │ @机器人
   ▼
飞书服务器 ──POST──▶ cloud-functions/feishu-webhook/index.ts
                     · 无状态请求模式，上限 120 秒
                     · 3 秒内 ACK（否则飞书重推）
                     · 验签 → 解密 → 生成 conversation_id → 加头转发
                          │
                          │ POST /feishu + Makers-Conversation-Id
                          ▼
                     agents/feishu/index.ts
                     · 会话模式，粘性路由，单次最长 900 秒（edgeone.json）
                     · 校验自制头 INTERNAL_TOKEN（未配则 fail closed）
                     · 跑模型 → 回飞书
```

**为什么必须拆**：EdgeOne 的 `agents/*` 路由**强制**要求 `Makers-Conversation-Id`
请求头，缺了返回 400。而飞书事件推送是**飞书服务器发的**，加不了自定义头。
所以 `agents/` 不能直接当回调地址，必须有个中间层补头；中间层自己不能用
`agents/`（否则同样要那个头），所以放 `cloud-functions/`。

**为什么中间层转发只能走 HTTP**：`cloud-functions/` 拿到的 `context` 只有
`request / env / agent.store`，**没有**「调用某个 agent」的能力。
`context.agent.store` 是共享数据（读写对话消息），不是调用入口。

### ⚠️ conversation_id 长度这个坑（会静默 400）

| | 值 | 长度 |
|---|---|---|
| 飞书 chat_id 实际形状 | `oc_` + 32 位十六进制 | **35** |
| 原版照抄的拼法 | `fs-` + 上面那串 | **38** |
| EdgeOne 上限 | 6~36 字符，仅 `0-9 a-z A-Z - _ .` | **36** |

超限。本地用短 id 测试一切正常，**线上真实会话全挂**。
现方案：`fs-` + `SHA-256(chatId)` 前 32 位十六进制，**恒为 35 字符**。
哈希是**确定性**的 —— 同一个 chat 永远映射同一个 conversation_id，
这是粘性路由成立的前提，不能换随机 id。

## 2. 目录结构

```
agents/feishu/          agents 路由（会话模式）
  index.ts              入口；路由 POST /feishu，含 ?probe=1 自测端点
  _host.ts              宿主能力抽象（模型客户端、store 接入）
  _tools.ts             工具装配（五个来源，见 §4）
  _instructions.ts      系统提示词
  _search.ts            自建 web_search（serper）
  _diag.ts              诊断计数器（/agent-metrics）

cloud-functions/feishu-webhook/index.ts   无状态转发层

src/feishu/             平台无关的飞书逻辑（大部分原样从原版移植）
  crypto.ts   验签/解密      event.ts    事件解析
  api.ts      飞书 API 调用  card.ts     卡片
  streamer.ts 流式更新       turn.ts     回合编排
  store.ts    会话 KV        global-memory.ts  跨会话长期记忆
  docs.ts     云文档工具族   oauth.ts / user-token.ts  用户授权
  compact.ts  会话压缩       commands.ts 命令分发
  session-sanitize.ts / types.ts

src/ghworkspace/        agent 自己的工作区仓库（client.ts / tools.ts）
src/shared/             base64 / util
bridge/                 launchd 本地桥（含 sync-env.mjs）
tools/                  ask-bot.mjs / verify-memory.mjs（运维脚本）
test/smoke.ts           冒烟测试（README 称 173 项）
docs/                   01 架构与移植映射 / 02 飞书配置 / 03 验证清单
```

## 3. 存储三层

| 层 | 载体 | 物理键 | 放什么 | 一致性 |
|---|---|---|---|---|
| ① 会话态 | `context.store.state`（按 conversation_id 隔离的 JSON KV） | `state/<conversation_id>/<key>` | 去重 / 限流 / token 缓存 / 语料快照 | 进程内权威副本 + 写穿；**非分布式锁**，只在同会话单实例时正确 |
| ② 对话消息 | `context.store.openaiSession()` | 平台托管 | 多轮对话历史 | 平台提供，**无压缩钩子** |
| ③ 跨会话事实 | **Blob**，命名空间 `agent-memory-<projectId>` | `prefs/<key>`、`user/<openId>/<key>` | 长期记忆 | Blob set 无 TTL、**整值覆盖、无条件写** |

**③ 的两个设计决定**（`src/feishu/global-memory.ts`）：
- **一条事实一个键** —— 因为 set 是整值覆盖、没有条件写，两件事塞一个 key 会互相覆盖。
- **刻意不复用平台的 `memory-<projectId>`** —— 那个命名空间用 list 按前缀枚举，怕误碰用户数据。
- 运行时从 `globalThis.__EDGEONE_AGENT_RUNTIME__.getStore` 取，凭证**构建期注入**。

## 4. 工具族（五个来源，`agents/feishu/_tools.ts`）

| 来源 | 工具 |
|---|---|
| 自建 `_search.ts` | `web_search`（serper） |
| 平台 `context.tools.*` | `code_interpreter` / `commands` / `files_*` / `browser_*` |
| `src/feishu/docs.ts` | `feishu_doc_read` / `feishu_sheet_read` / `feishu_bitable_read` / **`feishu_docx_create`** / `feishu_bitable_write` / `feishu_sheet_write` / `feishu_docx_write` |
| `src/feishu/global-memory.ts` | `remember_fact` / `forget_fact` / `recall_facts` |
| `src/ghworkspace/tools.ts` | `ws_ls` / `ws_read` / `ws_write` / `ws_rm`（配 `GITHUB_WORKSPACE_TOKEN` 才挂） |

**踩过的坑**：
- 平台自带的 `web_search` 底层是腾讯云 WSA，本项目没配 `WSA_API_KEY`，**一调就报错**。
  所以换成自建，靠 `extraExcluded` 把平台同名工具**摘掉**，否则模型可能选中坏的。
- 工具名来自官方文档的表 —— 名字是模型选工具的唯一依据，**写错等于工具不存在**。
- 卡片摘要的字段匹配**有顺序要求**（`count` 太通用必须排后面；`docUrl` 判据要排在
  `appended` 前面），见 `_tools.ts` 注释。

## 5. 已知缺口与未知数

**三个硬缺口**（对比 Cloudflare 原版）：
1. 无 RPC 寻址（原版 `getAgentByName`）→ 绕过去了
2. 无强一致 SQL（原版 `ctx.storage.sql`）→ 绕过去了
3. **无 alarm**（原版 `this.schedule()`）→ **没绕过去，换了个做法**

**第三点的做法**：飞书要 3 秒内 ACK，模型要跑二三十秒。现在的办法是
**先回 202，再在后台跑完**。而「返回 Response 之后未 await 的异步代码还能不能跑完」
官方没有明文承诺 —— 所以：
- 有 `?probe=1` 自测端点
- 有 `FEISHU_DISPATCH_MODE=sync` 兜底开关
- **README 记录：线上实测成立**（`phase: finished` / `elapsedMs: 15046`，保持 `async`）

**其他**：
- 会话压缩**自动化没有**（`openaiSession()` 不暴露压缩钩子），改成手动 `/compact` `/clear`
- `edgeone makers dev` 本地起得来但 **agent 路由打不到**（`agent-node` 不绑定端口）
- 飞书**入站** webhook（事件订阅那段）**没跑过**；已验证的是直调 `?mode=sync`
- 【未核】流事件的实际名字（要部署后看 `/agent-metrics`）

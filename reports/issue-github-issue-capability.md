# 工单：让 agent 具备提 GitHub issue 的能力

**仓库**：`guci314/edgeone-agent-lab`
**类型**：feature / capability
**读码基准**：HEAD `e7b59db`（2026-09-25）

> 按 GitHub issue 格式写，可直接复制到 `edgeone-agent-lab`。
> 交 Claude Code 的话贴「背景 / 配置改动 / 代码任务 / 验收」四节。

---

## 背景

agent 现在有 `ws_*` 四件（读写自己的工作区仓库 `guci314/cf-agent-workspace`），
但**没有提 issue 的能力**。

实际痛点：用户在飞书里让 agent「把这个 report 提个工单」，agent 只能把内容写进工作区，
用户还得自己复制粘贴到目标仓库去开 issue —— 中间那步本可以自动化。

**`src/ghworkspace/client.ts` 文件头已写明现状**：

> 凭证是 fine-grained PAT，**只授予这一个仓库的 Contents 读写**。
> 在 EdgeOne 侧配的是普通环境变量 `GITHUB_WORKSPACE_TOKEN`。

⚠️ **所以这不只是「加个工具」，而是「扩权」** —— GitHub 的 Issues API 不属于
Contents 权限范围，**现有 token 提不了 issue**。这是本工单最需要被认真对待的部分。

---

## 设计取舍（先定，再动手）

### 取舍 1：写到哪里？

| 方案 | 说明 | 评价 |
|---|---|---|
| A. 扩权**现有** token，让它对**指定仓库**也能开 issue | 加 `GH_ISSUE_REPOS` 之类的白名单 | ✅ 推荐 |
| B. 新建**独立** token，只授 Issues 写 | 权限隔离、互不影响 | ✅ 更安全，但要配两个密钥 |
| C. 只授 **Contents** 的 token 用 Contents API 变通 | — | ❌ 做不到，issue 不在 Contents 下 |

**建议 A 或 B，倾向 B**：现有 token 是 Contents 读写，若为开 issue 而扩权，
一旦泄漏影响面同时扩大。独立 token 的爆炸半径更小。

**但无论选哪个，都必须有仓库白名单。**

### 取舍 2：只开 issue，还是也能评论 / 关闭？

**建议只做「开 issue + 加评论」，不做关闭。**

- 开 issue 是可逆的（能关），风险可控
- 关闭别人提的 issue、改标题，是**破坏性且面向他人**的操作 ——
  agent 误操作一次就影响协作者，收益远小于风险
- 与仓库既有约定一致：`ws_rm` 的存在理由就是「不做目录删除」，
  `EXCLUDED` 里也刻意排除了 `files_remove`（「留着反而多一个误删的机会」）

### 取舍 3：要不要目标仓库白名单？

**必须要，且是硬约束。** 理由与 `ghWorkspaceConfig` 现有做法一致：

> 认不出 owner/name 就当作没配：宁可没有工具，也不要拿一个拼错的仓库名去 404，
> 那种错看起来像「仓库不存在」，实际是配置问题

**没有白名单 = token 能开的仓库全都能开。** 绝不能这样。

---

## 配置改动

### 1. 新环境变量（按取舍 2 选 B 时）

```bash
# ── GitHub issue（可选）──────────────────────────────────────────────
# 配了才挂 gh_issue_* 工具。fine-grained PAT，只授下列仓库的 Issues: Read and write。
# ⚠️ 普通环境变量，别用 AI_GATEWAY_*（会被 deploy 覆盖，见 docs/02 排错表）。
GITHUB_ISSUE_TOKEN    github_pat_…
# 允许开 issue 的仓库白名单，逗号分隔。**留空则整个工具族不挂**。
GITHUB_ISSUE_REPOS    guci314/edgeone-agent-lab,guci314/cf-agent-workspace
```

**要点**：
- 白名单**留空 = 不挂工具**（沿用 `ghWorkspaceConfig` 的规矩：
  「配不全就当没配，别挂出一族永远失败的工具让模型反复去试」）
- 名称用 `GITHUB_ISSUE_*` 而非复用 `GITHUB_WORKSPACE_*` —— 两者权限不同，混用会让
  「改工作区 token」这个动作意外影响 issue 能力
- 同步更新 `docs/02 · 飞书后台配置` 的环境变量清单

### 2. 权限最小化（**必须写进工单，别漏**）

GitHub fine-grained PAT 权限选择：

- ✅ **Issues: Read and write**
- ✅ Repository access: **Only select repositories** → 只勾白名单里那几个
- ❌ **不要**勾 Contents / Actions / Administration

**在 GitHub 侧把范围收紧，比在代码里判白名单更可靠** ——
代码白名单是第一道，token 权限是第二道，两道都要有。

---

## 代码任务

### 1. 新增 `src/ghworkspace/issues.ts`（或并入 client.ts）

**照 `client.ts` 的既有写法**：

- 纯 `fetch`，**不引 SDK**（现注释：「只有四个端点，不值得一个依赖」）
- 复用 `ghWorkspaceConfig` 的 `ghConfigIsUsable` 式校验思路：
  白名单为空 / 格式不合法 → 返回 null
- **凭证只出现在请求头，绝不进任何错误信息**
  （`client.ts` 明文要求：「错误信息会被模型读、被飞书卡片渲染、被用户复制出去」）
- 超时给宽（参考 `GET_TIMEOUT_MS = 25_000` / `WRITE_TIMEOUT_MS = 30_000` 的理由：
  「等的久」远好过「明明能成却报错」）
- **区分「模型能自己纠正的用法错」与「环境故障」** ——
  `client.ts` 已定义了这个分界（拿错工具/仓库不在白名单 vs 网络故障），
  照它办，别让模型对「仓库不在白名单」去重试或道歉

**端点**（GitHub Issues API）：
- `POST /repos/{owner}/{repo}/issues` —— 开 issue
- `POST /repos/{owner}/{repo}/issues/{n}/comments` —— 加评论

### 2. 工具装配

`src/ghworkspace/tools.ts` 增两个工具，并在 `agents/feishu/_tools.ts` 挂上：

- `gh_issue_create` —— 参数：仓库（**必须在白名单内**）、标题、正文
- `gh_issue_comment` —— 参数：仓库（白名单内）、issue 号、正文

**白名单校验要在工具层做，且拒绝时给出明确原因**（哪个仓库、为什么不允许），
不要静默失败。

### 3. 提示词

`agents/feishu/_instructions.ts` 里，工作区那段提示词（`WORKSPACE_PROMPT`）
旁边补一段 issue 用法说明。**参考现有写法**：那份提示词专门讲过
「`files_*` 是沙箱里的临时目录，不是用户的磁盘」这类**容易误解的边界** ——
issue 这边同理，要讲清「只能开到白名单里的仓库」。

---

## 验收标准

- [ ] `npm run typecheck` 零错误
- [ ] `npm test` 全绿
- [ ] **白名单外仓库被拒绝**，且错误信息说明了原因（不是静默失败）
- [ ] **未配 `GITHUB_ISSUE_TOKEN` 时工具族整个不挂**（不是挂上但一调就错）
- [ ] 未配 `GITHUB_ISSUE_REPOS` 时同样不挂
- [ ] **错误信息里不含 token**（写个单测断言，别靠眼看）
- [ ] 实际开出一个 issue 并 `gh_issue_comment` 成功（在测试仓库上验）
- [ ] `docs/02` 环境变量清单已更新
- [ ] 部署后对着 `/agent-metrics` 确认工具**实际注册的名字**

---

## ⚠️ 安全注意（请勿省略）

1. **token 不进工作区仓库**。`cf-agent-workspace` 是 GitHub 上的仓库，
   一旦提交就永久留在 git 历史里 —— 这正是 agent 现有提示词里
   「绝不把密钥写进工作区」那条规矩的由来。**写配置一律用占位符。**

2. **本工单是一次能力扩张**。agent 现在能对外部仓库产生**公开可见的副作用**
   （issue 是别人也能看到的）。请确认这是想要的 ——
   issue 能被删，但通知已经发出去了，撤回不了通知。

3. **建议加一条审计日志**：每次开 issue 记录
   （时间 / 仓库 / 标题 / 谁要求的）。与 `_diag.ts` 的既有做法一致 ——
   那里加计数器的理由就是「可选钩子会静默失效，没计数器就分不清有没有生效」。

4. 若暂时不想扩权，**降级方案**：agent 在工作区里生成一段**排版好的 issue markdown**，
   附上「复制到 X 仓库即可提交」的说明。这不需要任何新凭证 ——
   就是本工单开头描述的那个现状，但可以把格式做得更省事。

---

## 参考

- `src/ghworkspace/client.ts`（现有 token 用法与错误分界）
- `src/ghworkspace/tools.ts`（现有 ws_* 工具装配）
- `agents/feishu/_tools.ts`（五个工具来源的装配点）
- `docs/02-飞书后台配置.md`（环境变量清单，第 178 行起）
- 架构笔记：`cf-agent-workspace/notes/edgeone-agent-lab-架构.md`

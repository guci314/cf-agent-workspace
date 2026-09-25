# 工单：agent 自改代码的能力（可行性已实测）

**仓库**：`guci314/edgeone-agent-lab`
**类型**：capability / 自举
**读码基准**：HEAD `e7b59db`（2026-09-25）
**结论**：**技术上已经可行**。瓶颈不在沙箱能力，而在 ①凭证 ②安全边界。

> 按 GitHub issue 格式写。交 Claude Code 时贴「实测结论 / 缺口 / 建议方案 / 风险」四节。

---

## 一、实测结论：沙箱编程能力**充足**

本次在**真实的对话沙箱**里跑通（不是推断）：

| 项 | 实测值 |
|---|---|
| CPU / 内存 / 磁盘 | 3 核 / 4.1 GB / 5 GB（可用 4.7 GB） |
| Node / npm / Python / git | v24.21.0 / 11.19.0 / 3.12.13 / 2.47.3 |
| 公网 | ✅ `github.com` 200、`registry.npmjs.org` 200 |
| 权限 | uid=1000，**有 sudo** |
| `edgeone` CLI | ✅ 已装，`/usr/local/bin/edgeone`（v1.6.x） |

**端到端验证过**：

```bash
git clone --depth 1 https://github.com/guci314/edgeone-agent-lab.git
npm install                      # ✅ 成功
npx tsc --noEmit                 # ✅ 通过，零错误
npm test                         # ✅ 全部通过：173 项
```

**所以「写代码 + 自己验证」这一环已经通了。** 不需要新增任何东西。

---

## 二、缺口：差的是「凭证」，不是「能力」

### 缺口 1：部署认证

```
$ edgeone whoami
[✘] You are not authenticated. Please run `edgeone login`,
    or set EDGEONE_PAGES_API_TOKEN.
```

沙箱里**未认证**。但 CLI **明确支持环境变量**：
`EDGEONE_PAGES_API_TOKEN`（非交互环境也可用 `-t <token>`）。

> `README.md:39` 已记录：令牌可从 `~/.edgeone/<sha256>`（JSON，取 `value.Token`）捞。

### 缺口 2：改不了「自己正在跑的那份」代码

⚠️ **这条最容易误解，必须讲清。**

沙箱是个**隔离容器**，里面 `/tmp/eo2` 那份 clone 是**副本**。
在里面改代码，**绝不会影响正在服务你的那个实例** —— 直到它被部署上去。

所以「自改代码」实际是三步：

```
① 在沙箱里 clone → 改 → 自测（✅ 已具备）
② 提交回 GitHub            ← 目前只能 push 到 cf-agent-workspace，见缺口 3
③ 触发部署                 ← 需要凭证（缺口 1）
```

### 缺口 3：写权限只覆盖工作区仓库

现有 `GITHUB_WORKSPACE_TOKEN` 是 fine-grained PAT，
**只授 `guci314/cf-agent-workspace` 的 Contents 读写**（`client.ts` 文件头明文）。
它**改不了 `edgeone-agent-lab` 本身**。

---

## 三、两条可行路径

### 路径 A：推 Git，让平台自动构建（**推荐**）

`README.md:92`：

> 部署：**推到 Git 仓库让 Makers 自动构建**，或 `npm run deploy`。

**做法**：给 agent 一个能写 `edgeone-agent-lab` 的凭证 → clone / 改 / 自测 / push
→ 平台侧自动构建部署。

**优点**：
- **不需要 EdgeOne 凭证**（绕开缺口 1）
- 走 Git 有完整历史，**改动可回溯、可 revert**
- 可以要求它**开 PR 而非直推 main**，人审后再合 —— 见第四节

**缺点**：
- 平台侧自动构建**不会跑 `npm test`**，测试得在沙箱里自己跑（已具备）
- 构建失败要到平台日志才看得到

### 路径 B：沙箱内直接 deploy

需要 `EDGEONE_PAGES_API_TOKEN`。

**缺点较多**：
- `docs/03:330-370` 记了**三个实测坑**：别带路径参数、先删项目根 zip、
  要 `env -u NODE_OPTIONS` 跑（否则卡在 `Pre-build hook triggered` 十几分钟）
- 部署会**重置 `AI_GATEWAY_*`**
- 没有 Git 历史，出问题不好回退

**不建议**，除非有必须绕开 Git 的理由。

---

## 四、⚠️ 风险（本工单最该被认真读的部分）

### 风险 1：这是**最高权限的自我修改**

给 agent 改 `edgeone-agent-lab` 的能力 = 它能改**自己的提示词、自己的工具集、
自己的安全边界**（`INTERNAL_TOKEN` 校验、白名单、`EXCLUDED` 列表）。

**一次错误改动可以让它自己敞开后门，而这是它自己写的代码。**

建议的护栏（**至少要有一条**）：

- **强制 PR，不许直推 main** —— 人审后才合。这是开销最小、效果最好的一条
- 或：改动限特定路径（如 `src/`、`agents/`），**禁改** `.env` / 部署配置 / 鉴权代码
- 或：所有自改的 commit 打标记 + 通知人（沿用 `_diag.ts` 的审计思路）

### 风险 2：凭证泄漏面

无论是 GitHub PAT 还是 EdgeOne token，**都不能进工作区仓库**
（那是 GitHub 上的仓库，提交了就永久留在 git 历史）。

⚠️ 且要意识到：**agent 能读自己的环境变量**。若把「能改自己代码的 token」
放进它自己的 env，那么它一旦被提示注入诱导，就**可能把 token 写出去**。
这是路径 A/B 共有的固有风险，**值得独立评估**。

### 风险 3：自我修改的不可控循环

若允许它根据线上表现自动改进自己，可能出现「越改越偏」而无人察觉：
- 建议**所有自改都必须留痕**（Git 历史天然满足此条，前提是走路径 A）
- 建议**首次启用时只给「开 PR」权限**，观察一段时间再考虑放开

---

## 五、建议的最小起步

**先做最小可验证的一步，别一上来就全放开**：

1. 建一个 fine-grained PAT，**只授 `guci314/edgeone-agent-lab` 的 Contents 读写**
2. 环境变量命名与现有风格一致，如 `GITHUB_SELF_TOKEN`；
   **不要**复用 `GITHUB_WORKSPACE_TOKEN`（两者作用域不同，混用会让改工作区 token
   意外影响自改能力）
3. 工具只给 `gh_pr_create`（开 PR）**而非直接 push**
4. 提示词里写死：**自改必须开 PR，不得直推 main**
5. 走一遍完整流程验一次：clone → 改一处 → `npm test` → 开 PR → 人审 → 合 → 平台构建

**跑通这一步再谈要不要放开。**

---

## 六、验收标准（最小起步版）

- [ ] `npm run typecheck` / `npm test` 在沙箱里全绿（**已实测具备**）
- [ ] 自改工具**只能在 `edgeone-agent-lab` 上开 PR**，推不动别的仓库
- [ ] **直推 main 被拒绝**，且错误信息说明原因
- [ ] 开出的 PR 里**含测试结果**（说明自测跑过）
- [ ] token **不出现在任何错误信息**里（写单测断言）
- [ ] 全流程实测一次：改一处真代码 → 开 PR → 合并 → 平台构建成功

---

## 七、一句话总结

**沙箱能力早就够了（173 项测试都在里面跑绿了）。真正要决定的是：
要不要给 agent 修改自己安全边界的能力，以及用什么护栏把它关住。**

建议从「只能开 PR、必须人审」起步。

---

## 参考

- 实测记录：本工单第一节
- `README.md:39`（未登录时的处理）、`README.md:92`（部署方式）
- `docs/03-验证清单.md:330-370`（deploy 的三个实测坑）
- `docs/02-飞书配置.md:178+`（环境变量清单）
- `src/ghworkspace/client.ts`（现有 token 的作用域与错误分界）
- 架构笔记：`cf-agent-workspace/notes/edgeone-agent-lab-架构.md`

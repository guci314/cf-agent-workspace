# 工单：agent 自改代码的能力（可行性已实测）

> ⚠️ **2026-09-26 决定：暂不做。** 用户拍板。**本工单不要当成待办去捡。**
>
> 决定与理由记在 `edgeone-agent-lab` 的 `docs/01-架构与移植映射.md` **第十一节
> 「刻意不做的事」**：技术上早已可行（沙箱能跑通全部测试、部署链路已自动化、
> agent 无需持有 EdgeOne 凭证），缺口只剩写权限 —— **正因为只差一步，才要写死
> 这个决定**。给它改自己代码的能力 = 它能手改自己的提示词、工具集、安全边界；
> 而 workflow 文件也在仓库里，能改它就等于能删掉 `npm test` 绕过门禁。
>
> 将来重启的最小起步（只给开 PR + 禁改 `.github/workflows/`）也写在那节里。

**仓库**：`guci314/edgeone-agent-lab`
**类型**：capability / 自举
**读码基准**：HEAD `e7b59db`（2026-09-25）
**结论**：**技术上已经可行，且比初版判断的更可行**。
瓶颈不在沙箱能力，也不在部署凭证（**GitHub Actions 已全部代劳**），
而在 **①写权限 ②安全边界**。

> 按 GitHub issue 格式写。交 Claude Code 时贴「实测结论 / 现有链路 / 缺口 / 建议方案 / 风险」五节。
>
> **修订记录**：初版曾把「部署认证」列为缺口 —— **该判断错误**。
> 实际部署走 `.github/workflows/deploy.yml`（push main 触发），
> token 由 Actions secrets 注入，**agent 无需持有任何 EdgeOne 凭证**。本版已更正。

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

**«写代码 + 自己验证» 这一环已经通了。**

⚠️ **一个已知限制**：沙箱**跨轮次会被清空**（实测：clone 的 `/tmp` 目录隔一轮就没了）。
每轮要重新 clone，**不能指望上一轮的现场还在**。

---

## 二、现有部署链路（读 `.github/workflows/deploy.yml` 确认）

**这条链路比预想的完整得多，是本次最重要的发现。**

```yaml
on:
  push:
    branches: [main]        # ← 只推 main 才触发
  workflow_dispatch:        # ← 也可手动触发

jobs:
  deploy:
    steps:
      - checkout
      - setup-node 22
      - npm install
      - npm run typecheck   # ⚠️ 门禁：挂了就不上线
      - npm test            # ⚠️ 门禁：挂了就不上线
      - rm -f edgeone-agent-lab.zip
      - npx edgeone makers deploy -n edgeone-agent-lab \
          -t "${{ secrets.EDGEONE_API_TOKEN }}" -a overseas --json
```

**四个关键点**：

1. **有硬门禁** —— `typecheck` 和 `npm test` **跑不过就不部署**。
   这比我原以为的「平台侧只构建不测试」强得多。
2. **agent 不需要任何 EdgeOne 凭证** —— token 是 `secrets.EDGEONE_API_TOKEN`，
   Actions 注入。workflow 文件头注释 4 亦明确：
   「环境变量都在 EdgeOne 控制台的项目 env 里，部署快照自动携带，
   **Actions 侧不配任何业务密钥**」。
3. **只推 main 触发** —— 这是道天然的门：
   开 PR 不会部署，**合并才部署**。
4. **`concurrency: deploy-production`** —— 同时只跑一个部署，不会互相踩。

**所以「自改代码」的真实路径只剩两步**：

```
① 在沙箱里 clone → 改 → 自测（✅ 已具备，无需新增任何东西）
② push 到 main → Actions 自动跑门禁 → 通过则部署（✅ 只需写权限）
```

**不需要沙箱内认证，也不需要 `edgeone login`。**
所有部署细节（`-n` / `-a overseas` / 清理 zip）都已在 workflow 里处理好了。

---

## 三、缺口：只剩「写权限」

现有 `GITHUB_WORKSPACE_TOKEN` 是 fine-grained PAT，
**只授 `guci314/cf-agent-workspace` 的 Contents 读写**（`client.ts` 文件头明文）。
**它改不了 `edgeone-agent-lab` 本身。**

这是唯一的实质缺口。补上它，整条链路就闭合了。

---

## 四、建议方案

### 给一个**只管开 PR** 的凭证（推荐）

1. 建 fine-grained PAT，**只授 `guci314/edgeone-agent-lab` 的 Contents 读写**
2. 环境变量命名与现有风格一致，如 `GITHUB_SELF_TOKEN`；
   **不要**复用 `GITHUB_WORKSPACE_TOKEN`（作用域不同，混用会让改工作区 token
   意外影响自改能力）
3. 工具**只给 `gh_pr_create`（开 PR）**，**不给直接 push main**
4. 提示词写死：自改必须开 PR，**不得直推 main**

**为什么这样最稳**：结合第二节的发现 —— **推 main 才部署**。
所以「只能开 PR」这个约束，**天然等于「改动必须经人合并才会上线」**。
护栏不是靠提示词自觉，而是**平台机制本身**。

### 完整闭环

```
agent 在沙箱改代码 → 自测（typecheck + 173 项测试）
  → 开 PR
  → 人审 + 合并
  → Actions 再跑一遍 typecheck + test（第二道门禁）
  → 通过则自动部署
```

**两道测试门禁 + 一次人工审查**，链路是完整的。

---

## 五、⚠️ 风险（本工单最该被认真读的部分）

### 风险 1：这是**最高权限的自我修改**

给 agent 改 `edgeone-agent-lab` 的能力 = 它能改**自己的提示词、自己的工具集、
自己的安全边界**（`INTERNAL_TOKEN` 校验、白名单、`EXCLUDED` 列表）。

**一次错误改动可以让它自己敞开后门，而这是它自己写的代码。**

**缓解**：「只能开 PR」+「推 main 才部署」已构成实质护栏（见第四节）。
若要更严，可再加：改动限特定路径（如 `src/`、`agents/`），
**禁改** `.github/workflows/`、`.env`、鉴权代码。

⚠️ **特别提示**：**workflow 文件本身也在仓库里**。
若能改 `.github/workflows/deploy.yml`，就能绕过测试门禁
（比如把 `npm test` 那步删掉）。**这是护栏的软肋，建议明确禁改该路径。**

### 风险 2：凭证泄漏面

无论是 GitHub PAT 还是别的 token，**都不能进工作区仓库**
（那是 GitHub 上的仓库，提交了就永久留在 git 历史）。

⚠️ 且要意识到：**agent 能读自己的环境变量**。若把「能改自己代码的 token」
放进它自己的 env，那么它一旦被提示注入诱导，就**可能把 token 写出去**。
**这是固有风险，值得独立评估。**

### 风险 3：自我修改的不可控循环

若允许它根据线上表现自动改进自己，可能出现「越改越偏」而无人察觉。
**缓解**：走 PR + Git 历史天然留痕；**首次启用时只给开 PR 权限**，观察一段时间。

---

## 六、建议的最小起步

1. 建 fine-grained PAT，只授 `edgeone-agent-lab` 的 Contents 读写
2. 命名 `GITHUB_SELF_TOKEN`（勿复用工作区那个）
3. 工具只给 `gh_pr_create`
4. 提示词写死「自改必须开 PR」
5. **明确禁改 `.github/workflows/`**（见风险 1 的软肋）
6. 跑通一次完整流程验一遍（见下）

---

## 七、验收标准（最小起步版）

- [ ] 沙箱里 `npm run typecheck` / `npm test` 全绿（**已实测具备**）
- [ ] 自改工具**只能在 `edgeone-agent-lab` 上开 PR**，推不动别的仓库
- [ ] **直推 main 被拒绝**，且错误信息说明原因
- [ ] 开出的 PR 里**附测试结果**（说明自测跑过）
- [ ] 改 `.github/workflows/` 被拒绝
- [ ] token **不出现在任何错误信息**里（写单测断言）
- [ ] 全流程实测：改一处真代码 → 开 PR → 合并 → **Actions 门禁通过** → 部署成功

---

## 八、一句话总结

**沙箱能力早就够了（173 项测试都在里面跑绿了），部署链路也早已自动化
（Actions 带双重测试门禁）。真正要决定的只剩一件事：
要不要给 agent 修改自己安全边界的能力，以及用什么护栏把它关住。**

**建议从「只能开 PR、必须人审 + 禁改 workflow」起步。**

---

## 参考

- `.github/workflows/deploy.yml`（部署链路全貌，**本次核心依据**）
- 实测记录：本工单第一节
- `README.md:39`（未登录时的处理）、`README.md:92`（部署方式）
- `docs/03-验证清单.md:330-370`（deploy 的三个实测坑）
- `docs/02-飞书配置.md:178+`（环境变量清单）
- `src/ghworkspace/client.ts`（现有 token 的作用域与错误分界）
- 架构笔记：`cf-agent-workspace/notes/edgeone-agent-lab-架构.md`

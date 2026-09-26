# agent-sandbox —— agent 的「试跑位」

这是 agent 自己写代码、并**自动部署上线**的地方。

最后更新：v5

## 它怎么工作

```
agent 改这里的文件 → commit 到 main
   → .github/workflows/deploy.yml 被触发
   → 跑 npm test（门禁，挂了就不部署）
   → 同时部署到 Cloudflare Pages 和 EdgeOne Pages
   → 得到两个公网 URL
```

## 目录约定

| 文件 | 用途 |
|---|---|
| `public/` | 静态资源。两边都发布这个目录 |
| `package.json` | `test` 脚本会被 CI 当**部署门禁**跑。没有这个文件就跳过测试 |
| `test/` | 测试放这 |
| `wrangler.toml` | Cloudflare 侧配置（project name 必须和目录名一致） |
| `edgeone.json` | EdgeOne 侧配置 |

## ⚠️ workflow 是 agent 可以自己改的

`.github/workflows/deploy.yml` 就在这个仓库里，agent 有 Contents 写权限，
所以**它能自己定义工作流** —— 改部署方式、加测试步骤、加新的部署目标都行。

这也意味着 workflow 里能拿到 `CLOUDFLARE_API_TOKEN` / `EDGEONE_API_TOKEN` 两个
Actions secret。这是**有意接受**的取舍（部署凭证不放在 agent 手里，但 agent
能通过改 workflow 间接用到它们）。

## 部署结果去哪看

workflow 跑完会把结果写回 **`.deploy-status.json`**（就在这个目录）：

```json
{ "project": "...", "sha": "...", "at": "...", "runUrl": "...",
  "test": "success", "cloudflare": "success", "edgeone": "success" }
```

所以 **agent 用 `ws_read` 就能看到上次部署成没成、跑的是哪个 commit** ——
不需要别的凭证。⚠️ 刚提交完那一刻它还是**上一次**的结果，核对时比一下里面的
`sha` 和你刚拿到的 commit。

这个 commit 由 workflow 用默认的 `GITHUB_TOKEN` 推，**不会触发新的 workflow**，
所以没有「部署完写状态 → 又触发部署」的循环。

# agent-sandbox —— agent 的「试跑位」

这是 agent 自己写代码、并**自动部署上线**的地方。

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

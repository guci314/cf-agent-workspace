# Bug: 缺少「创建云文档」能力 —— 机器人无法把内容写成一篇新的飞书文档

**报告日期**：2026-09-25
**仓库**：`guci314/edgeone-agent-lab`
**相关文件**：`src/feishu/docs.ts`（789 行，6 个工具）、`agents/feishu/_tools.ts`

---

## 现象

在飞书里让机器人「写一份研究报告」，机器人无法完成 —— 它没有地方可写。

根因不是「不会写」，而是**工具族里没有任何创建文档的能力**。当前 `docs.ts` 导出的六个工具全部要求**一个已存在的资源 URL**：

| 工具 | 对已存在资源做什么 |
|---|---|
| `feishu_doc_read` | 读文档 |
| `feishu_sheet_read` | 读表格区域 |
| `feishu_bitable_read` | 读多维表格记录 |
| `feishu_bitable_write` | 往已有表**加/改记录** |
| `feishu_sheet_write` | **覆盖**已有区域单元格 |
| `feishu_docx_write` | 往已有文档**末尾追加**段落 |

`feishu_docx_write` 的实现决定了这一点：

```js
// src/feishu/docs.ts  ~line 760
const doc = encodeURIComponent(ref.token);
await callDoc("POST", `/docx/v1/documents/${doc}/blocks/${doc}/children`, {
  index: -1,   // 追加到末尾
  children: paras.map(...),
});
```

`ref.token` 来自 `start(url)` 对**用户传入链接**的解析。**没有文档 → 没有 token → 没有 children 端点可打。**

代码里出现的 `batch_create`（约 line 639）是**往已有多维表格批量加记录**，不是建表/建文档。

---

## 这不是「飞书没有这个能力」

**飞书开放平台官方提供创建文档接口**（已查证，见文末出处）：

- HTTP：`POST https://open.feishu.cn/open-apis/docx/v1/documents`
- 权限：`docx:document` 或 `docx:document:create`，**开启其中任意一项即可调用**
- 支持 `tenant_access_token`（应用身份）**和** `user_access_token`（用户身份）
- 请求体：`title`（1~800 字符，纯文本）、`folder_token`（可选，不传为根目录）
- 返回：`document_id` —— 拼上域名即为文档 URL
- 频控：**每秒 3 次**（超出返回 400 / 99991400）

**所以这是本项目的实现缺口，不是平台限制。**

有一个设计细节值得注意：该接口**只接受标题，不支持带内容创建**（官方原文：「该接口仅支持指定文档标题，不支持带内容创建文档」）。这意味着创建后**仍需**调用现有那段 `blocks/{id}/children` 追加正文 —— **那部分代码已经写好了，缺的只是第一步「建」。**

---

## 影响

用户能想到的自然请求 ——「写一份报告」「建个会议纪要」「把结论整理成文档」——**当前全部无法完成**，除非用户先手动建好一篇文档、共享给机器人、再把链接发过来。

这条链路上每一步都要人工介入，机器人只能扮演「往别人建好的文档里贴一段」的角色。

对照：`ws_write`（工作区仓库）**可以新建文件**。所以「产出物要落进一个新容器」这件事，在工作区仓库那条路上是通的，在飞书云文档这条路上是断的 —— **能力不对称**。

---

## 建议

新增一个创建工具（名字待定，如 `feishu_docx_create`），内部打上述端点，拿到 `document_id` 后：

1. 返回文档 URL 给用户；
2. 可选：紧接着用现有的 `blocks/{doc}/children` 把首段内容写进去，让「一句话生成一篇文档」真的可用。

注意事项（均来自官方文档）：

- **权限范围**要开 `docx:document` 或 `docx:document:create`，并在飞书后台为应用申请 —— 这一步需要人工在开放平台配置；
- **频控每秒 3 次**，连续建多篇要退避；
- 若用 `tenant_access_token`，**只能指定该应用自己创建的文件夹**（原文：「此处仅可指定应用创建的文件夹」）；
- `folder_token` 不传即落在**根目录** —— 但要留意根目录是应用自己的云空间，用户可能需要被显式授权才能看到（`1770040 no folder permission` 与文件夹权限相关）。

---

## 复现步骤（本次会话实测）

1. 在飞书里请求「写一份研究报告，放进飞书文档」
2. 机器人回答：无法新建文档，需要用户提供已存在的文档链接
3. 用户追问「你无法新建一个 docx 吗」，机器人确认：**工具链里没有创建入口**

**未做的验证（如实标注）**：本次**没有**实际调用 `POST /docx/v1/documents`。上述接口参数、权限、频控、错误码**全部来自飞书官方文档**，不是在真实 tenant 上跑出来的。实施前应先用真实应用凭证打一次，确认权限与返回结构。

---

## 出处

- 创建文档（docx v1）：https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document/create?lang=zh-CN
- 文档概述（列出创建/读取/编辑/删除）：https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/docx-overview?lang=zh-CN
- 创建云文档（drive v1，可建文档/表格/多维表格，支持模板）：https://open.feishu.cn/document/docs/drive-v1/file/create-cloud-document?lang=zh-CN

## 代码引证

- 工具清单：`src/feishu/docs.ts` 第 294 / 383 / 507 / 591 / 663 / 725 行
- `feishu_docx_write` 追加实现：`src/feishu/docs.ts` 约第 750-775 行
- 工具装配与来源说明：`agents/feishu/_tools.ts` 第 6 行、第 145-160 行

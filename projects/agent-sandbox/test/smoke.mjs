// 部署门禁：这个脚本挂了，workflow 就不会部署。
// 现在只有一条 —— 证明门禁本身是通的，agent 往这里加真测试。
import { readFileSync } from "node:fs";

let failed = 0;
const ok = (cond, msg) => {
  console.log(`${cond ? "✅" : "❌"} ${msg}`);
  if (!cond) failed++;
};

const html = readFileSync(new URL("../public/index.html", import.meta.url), "utf8");
ok(html.includes("<title>"), "index.html 要有 <title>");
ok(html.length > 100, "index.html 不该是空壳");

console.log(failed ? `\n❌ ${failed} 项失败` : "\n✅ 通过");
process.exitCode = failed ? 1 : 0;

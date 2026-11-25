import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { makePreviewHook, tokenCount } from "./preview.mjs";

const lines = [
  "Running checkout tests",
  ...Array.from({ length: 160 }, (_, i) => `test_cart_${i + 1} ... ok`),
  "AssertionError: expected two cart items, received one",
  ...Array.from({ length: 160 }, (_, i) => `test_order_${i + 1} ... ok`),
  "1 failed, 320 passed",
];
const diagnosticLine = lines.indexOf("AssertionError: expected two cart items, received one") + 1;
const output = lines.join("\n");
const event = {
  toolName: "bash", content: [{ type: "text", text: output }],
  structuredContent: { output, exit_code: 1, truncated: false }, isError: true,
};

const directory = await mkdtemp(join(tmpdir(), "pi-preview-demo-"));
try {
  console.log(`示例测试日志：${lines.length} 行，${tokenCount(output)} tokens，退出码 1`);
  for (const arm of ["B", "C"]) {
    const result = await makePreviewHook(arm, 128, directory)(event);
    const meta = result?.details?.logPreview;
    if (!meta || meta.fallback) throw new Error(`无法生成预览：${meta?.fallback ?? "未触发"}`);
    console.log(`\n${arm} · ${arm === "B" ? "短尾" : "头尾"} · ${meta.tokens}/128 tokens`);
    console.log(result.content[0].text);
    const archive = await readFile(meta.path, "utf8");
    if (archive !== output || !result.isError || result.structuredContent.exit_code !== 1) {
      throw new Error("归档或退出状态与原始结果不一致");
    }
    console.log(`从归档读取第 ${diagnosticLine} 行：${archive.split("\n")[diagnosticLine - 1]}`);
  }
} finally {
  await rm(directory, { recursive: true, force: true });
}

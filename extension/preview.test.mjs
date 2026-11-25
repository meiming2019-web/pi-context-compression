import assert from "node:assert/strict";
import test from "node:test";
import { mkdtemp, readFile, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { makePreviewHook, tokenCount } from "./preview.mjs";

function bash(output, exit = 0) {
  return { toolName: "bash", content: [{ type: "text", text: output }],
    structuredContent: { output, exit_code: exit, truncated: false }, isError: exit !== 0 };
}

test("both budgets include the full marker; a native archive supplies the real head", async t => {
  const dir = await mkdtemp(join(tmpdir(), "pi-test-"));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const text = "HEAD\n" + "日志📚 <|endoftext|>\n".repeat(3100) + "TAIL\n";
  const path = join(dir, "native.txt");
  await writeFile(path, text);
  const event = bash("日志\n".repeat(200) + "TAIL\n", 7);
  event.structuredContent.truncated = true;
  event.details = { fullOutputPath: path, truncation: { totalLines: 3102 } };
  for (const arm of ["B", "C"]) {
    const reply = await makePreviewHook(arm, 128, dir)(event);
    const preview = reply.content[0].text;
    assert.equal(preview.includes("HEAD"), arm === "C");
    assert.ok(preview.endsWith("TAIL\n") && preview.includes(reply.details.logPreview.path));
    assert.ok(tokenCount(preview) <= 128 && !preview.includes("�"));
    assert.equal(tokenCount(preview), reply.details.logPreview.tokens);
    assert.equal(reply.structuredContent, event.structuredContent);
    assert.equal(reply.isError, true);
    assert.equal(await readFile(reply.details.logPreview.path, "utf8"), text);
    assert.match(preview, /exit 7/);
  }
});

test("untruncated native output is archived verbatim, short and unreadable results pass through", async t => {
  const dir = await mkdtemp(join(tmpdir(), "pi-test-"));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const hook = makePreviewHook("C", 96, dir);
  assert.equal(await hook(bash("short")), undefined);
  const text = "start" + "🐳".repeat(512) + "end";
  const event = bash(text);
  const reply = await hook(event);
  assert.equal(await readFile(reply.details.logPreview.path, "utf8"), text);
  assert.ok(reply.content[0].text.startsWith("start") && reply.content[0].text.endsWith("end"));
  event.details = { fullOutputPath: join(dir, "missing") };
  const fallback = await hook(event);
  assert.equal(fallback.content, undefined);
  assert.equal(fallback.details.logPreview.fallback, "ENOENT");
});

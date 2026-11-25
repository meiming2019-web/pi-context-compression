import assert from "node:assert/strict";
import test from "node:test";
import activate from "./index.ts";
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
  const markers = [];
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
    const marker = preview.match(/\[… \d+ line breaks omitted \| exit 7 \| read (.+) with offset\/limit\]/)[0];
    markers.push(marker.replace(/\d+ line breaks/, "N line breaks").replace(reply.details.logPreview.path, "PATH"));
    assert.equal(reply.details.logPreview.budget, 128);
  }
  assert.equal(markers[0], markers[1]);
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

test("a failed registration invalidates even a previous success receipt", async t => {
  const directory = await mkdtemp(join(tmpdir(), "pi-register-"));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const values = { PI_PREVIEW_ARCHIVE_DIR: directory, PI_PREVIEW_ARM: "B", PI_PREVIEW_TOKENS: "128" };
  for (const [key, value] of Object.entries(values)) {
    const original = process.env[key];
    process.env[key] = value;
    t.after(() => { if (original === undefined) delete process.env[key]; else process.env[key] = original; });
  }
  activate({ on(name, fn) { assert.equal(name, "tool_result"); assert.equal(typeof fn, "function"); } });
  const receipt = join(directory, "active.json");
  assert.deepEqual(JSON.parse(await readFile(receipt)), ["B", 128]);
  assert.throws(() => activate({ on() { throw new Error("registration failed"); } }), /registration failed/);
  await assert.rejects(readFile(receipt), { code: "ENOENT" });
});

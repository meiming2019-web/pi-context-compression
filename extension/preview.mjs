import { link, mkdir, open, symlink, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { Tiktoken } from "js-tiktoken/lite";
import ranks from "js-tiktoken/ranks/o200k_base";

const tokenizer = new Tiktoken(ranks);
const encode = text => tokenizer.encode(text, [], []);
const newlines = text => text.split("\n").length - 1;
export const tokenCount = text => encode(text).length;

async function readEdges(path, budget, totalLines) {
  const file = await open(path, "r");
  try {
    const { size } = await file.stat();
    if (!Number.isSafeInteger(totalLines) || !size) throw new Error("missing archive metadata");
    // Only encode edge windows, even for multi-gigabyte logs. A gap at a UTF-8
    // boundary is in the omitted middle; the original archive stays byte-exact.
    const width = Math.min(size, Math.max(8192, budget * 16));
    async function slice(start) {
      const bytes = Buffer.alloc(width);
      const read = await file.read(bytes, 0, width, start);
      if (read.bytesRead !== width) throw new Error("incomplete archive read");
      let first = 0;
      if (start > 0) {
        while (first < width && (bytes[first] & 0xc0) === 0x80) first++;
      }
      return new TextDecoder("utf8", { ignoreBOM: true }).decode(bytes.subarray(first),
        { stream: start + width < size });
    }
    const head = await slice(0);
    const tail = width === size ? head : await slice(size - width);
    return { head, tail, bytes: size, breaks: totalLines - Number(!tail.endsWith("\n")) };
  } finally {
    await file.close();
  }
}

function edge(text, tokens, count, head) {
  if (!count) return "";
  const selected = head ? tokens.slice(0, count) : tokens.slice(-count);
  const decoded = tokenizer.decode(selected);
  // A single Unicode character can span several tokens.
  if (head) return text.startsWith(decoded) ? decoded : decoded.replace(/\uFFFD+$/, "");
  return text.endsWith(decoded) ? decoded : decoded.replace(/^\uFFFD+/, "");
}

function preview(arm, budget, path, exit, source) {
  const marker = n => `\n[… ${n} line breaks omitted | exit ${exit} | read ${path} with offset/limit]\n`;
  const headTokens = arm === "C" ? encode(source.head) : [];
  const tailTokens = encode(source.tail);
  let room = budget - tokenCount(marker(source.breaks));
  while (room >= 2) {
    const left = arm === "C" ? Math.floor(room / 2) : 0;
    const head = edge(source.head, headTokens, left, true);
    const tail = edge(source.tail, tailTokens, room - left, false);
    const missing = source.breaks - newlines(head) - newlines(tail);
    if (missing < 0 || Buffer.byteLength(head) + Buffer.byteLength(tail) >= source.bytes) {
      room = Math.floor(room / 2);
      continue;
    }
    const text = head + marker(missing) + tail;
    const tokens = tokenCount(text);
    if (tokens <= budget) return { text, tokens };
    room -= tokens - budget;
  }
  throw new Error("archive marker exceeds budget");
}

export function makePreviewHook(arm, budget, directory) {
  let sequence = 0;
  async function archive(output, nativePath) {
    await mkdir(directory, { recursive: true, mode: 0o700 });
    for (;;) {
      const file = join(directory, `log-${String(++sequence).padStart(6, "0")}.txt`);
      try {
        if (nativePath) {
          // Stable marker length across arms; reuse Pi's bytes without copying the log.
          try {
            await link(nativePath, file);
          } catch (err) {
            if (err.code !== "EXDEV") throw err;
            await symlink(nativePath, file);
          }
        } else {
          await writeFile(file, output, { flag: "wx", mode: 0o600 });
        }
        return file;
      } catch (err) {
        if (err.code !== "EEXIST") throw err;
      }
    }
  }

  return async function onResult(event) {
    if (event.toolName !== "bash" || event.content.length !== 1 || event.content[0].type !== "text") return;
    const originalTokens = tokenCount(event.content[0].text);
    if (originalTokens <= budget) return;
    const metadata = { arm, budget, originalTokens };
    const raw = event.structuredContent;
    try {
      if (!Number.isInteger(raw?.exit_code)) throw new Error("no native exit status");
      let path = event.details?.fullOutputPath;
      let source;
      if (path) {
        metadata.route = "pi_archive";
        source = await readEdges(path, budget, event.details.truncation?.totalLines);
        path = await archive(undefined, path);
      } else {
        if (raw.truncated || typeof raw.output !== "string") throw new Error("no complete log");
        metadata.route = "self_archive";
        path = await archive(raw.output);
        source = { head: raw.output, tail: raw.output, bytes: Buffer.byteLength(raw.output), breaks: newlines(raw.output) };
      }
      const { text, tokens } = preview(arm, budget, path, raw.exit_code, source);
      return {
        content: [{ type: "text", text }], structuredContent: raw, isError: event.isError,
        details: { ...event.details, logPreview: { ...metadata, path, tokens } },
      };
    } catch (err) {
      return { details: { ...event.details, logPreview: {
        ...metadata, fallback: err.code ?? err.message, tokens: originalTokens,
      } } };
    }
  };
}

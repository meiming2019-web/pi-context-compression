// Pi 1.6.0 invokes tool_result once, before persisting the tool message.
import { rmSync, writeFileSync } from "node:fs";
import { isAbsolute, join } from "node:path";
import { makePreviewHook } from "./preview.mjs";

export default function activate(pi) {
  const arm = process.env.PI_PREVIEW_ARM;
  const budget = Number(process.env.PI_PREVIEW_TOKENS);
  const directory = process.env.PI_PREVIEW_ARCHIVE_DIR;
  if (!["B", "C"].includes(arm) || !Number.isInteger(budget) || budget < 64 ||
      budget > 4096 || !directory || !isAbsolute(directory)) {
    throw new Error("Expected arm B/C, a 64–4096 token budget and an absolute archive directory");
  }
  const receipt = join(directory, "active.json");
  rmSync(receipt, { force: true });
  pi.on("tool_result", makePreviewHook(arm, budget, directory));
  writeFileSync(receipt, JSON.stringify([arm, budget]));
}

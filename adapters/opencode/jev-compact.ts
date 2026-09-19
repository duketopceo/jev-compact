// jev-compact adapter for OpenCode — retention-filter augmentation.
//
// On `experimental.session.compacting` (fires before the summarizer
// runs), this plugin fetches the session transcript through the plugin
// SDK client, runs `python3 -m jev_compact compact`, and pushes the
// result into output.context — so the compaction prompt sees verbatim
// load-bearing spans, the moving highlight, and tombstone receipts.
//
// Posture: augment. `output.prompt` can replace the compaction prompt
// entirely, but a summarizer LLM still mediates it — the honest win is
// feeding it verbatim retained content. Tombstoned spans restore via
// the jev-compact restore MCP server.
//
// Install: copy or symlink this file into ~/.config/opencode/plugins/.
// jev_compact must resolve for python3 (pipx install, or PYTHONPATH
// pointing at a checkout's src/, or JEV_PYTHONPATH set explicitly).

import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const BUDGET = process.env.JEV_BUDGET_TOKENS || "8000";
const STORE_DIR = process.env.JEV_STORE_DIR || ".jev-compact";
const TIMEOUT_MS = 120_000;
const MAX_CONTEXT_CHARS = 400_000;

// Dev-checkout fallback: this file lives at adapters/opencode/jev-compact.ts.
const REPO_SRC = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..", "src");

function childEnv() {
  const env = { ...process.env };
  if (!env.PYTHONPATH && env.JEV_PYTHONPATH) env.PYTHONPATH = env.JEV_PYTHONPATH;
  if (!env.PYTHONPATH) env.PYTHONPATH = REPO_SRC;
  return env;
}

// SDK message -> jev-compact generic NDJSON events.
function toEvents(messages) {
  const events = [];
  for (const m of messages || []) {
    const info = m?.info || m || {};
    const role = info.role || "other";
    const parts = m?.parts || [];
    for (const part of parts) {
      const type = part?.type || "";
      if (type === "text" || type === "reasoning") {
        const kind = role === "user" ? "user_turn" : "assistant_text";
        events.push({ kind, text: String(part?.text || "") });
      } else if (type === "tool" || type === "tool_call" || type === "tool_use") {
        const name = part?.tool || part?.name || "tool";
        events.push({ kind: "tool_call", text: `${name}: ${JSON.stringify(part?.state?.input ?? part?.input ?? {})}` });
        const out = part?.state?.output ?? part?.output;
        if (out !== undefined) events.push({ kind: "tool_result", text: typeof out === "string" ? out : JSON.stringify(out) });
      }
    }
    if (!parts.length && typeof info.text === "string" && info.text) {
      events.push({ kind: role === "user" ? "user_turn" : "assistant_text", text: info.text });
    }
  }
  return events;
}

export const JevCompactPlugin = async (ctx) => {
  return {
    "experimental.session.compacting": async (input, output) => {
      try {
        const sessionID = input?.sessionID;
        if (!sessionID || !ctx?.client?.session?.messages) return;

        const res = await ctx.client.session.messages({ path: { id: sessionID } });
        const messages = res?.data ?? res;
        const events = toEvents(messages);
        if (!events.length) return;

        const dir = mkdtempSync(join(tmpdir(), "jev-compact-"));
        try {
          const transcriptPath = join(dir, "transcript.ndjson");
          const outPath = join(dir, "out.md");
          writeFileSync(transcriptPath, events.map((e) => JSON.stringify(e)).join("\n"));

          const storeDir = join(ctx.directory || ".", STORE_DIR);
          spawnSync(
            "python3",
            ["-m", "jev_compact", "compact",
              "--transcript", transcriptPath,
              "--budget", String(BUDGET),
              "--scorer", "auto",
              "--store", storeDir,
              "--out", outPath,
              "--json"],
            { env: childEnv(), timeout: TIMEOUT_MS, stdio: "ignore" },
          );

          const doc = readFileSync(outPath, "utf8");
          if (doc && doc.length <= MAX_CONTEXT_CHARS) {
            output.context.push(
              "jev-compact retention context — verbatim spans the summary " +
              "must preserve exactly (paths, code, errors, decisions). " +
              "Tombstoned regions restore via the jev-compact restore MCP server.\n\n" + doc,
            );
          }
        } finally {
          rmSync(dir, { recursive: true, force: true });
        }
      } catch {
        // Never break compaction on adapter failure.
      }
    },
  };
};

export default JevCompactPlugin;

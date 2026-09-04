#!/usr/bin/env node
// babel-fish SessionStart hook. Runs the runtime's update check per
// policy (off / nudge / auto), then kicks off session vocabulary mining.

import { runSessionStart } from "@theglitchking/claude-plugin-runtime";
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";

// Mining is best-effort: it must never delay or fail session start, so it is
// detached with output discarded and nothing is awaited. It reads only
// transcripts changed since the last run (see mine-sessions.py's cursor).
//
// Timing: SessionStart sees transcripts through the PREVIOUS session — the
// current one isn't written yet — so an alias lands one session after it is
// first used. Accepted; a SessionEnd hook would be exact but is a second hook
// for one session of latency.
function mineVocabulary(cwd) {
  try {
    const script = join(cwd, ".claude", "project-map", "mine-sessions.py");
    if (!existsSync(script)) return; // marketplace install that skipped the copy

    const python = ["python3", "python"].find(
      (bin) => spawnSync(bin, ["--version"], { stdio: "ignore" }).status === 0
    );
    if (!python) return; // no interpreter — nothing to do, and nothing to say

    spawn(python, [script], {
      cwd,
      detached: true,
      stdio: "ignore",
    }).unref();
  } catch {
    // never surface: a mining failure must not affect session start
  }
}

await runSessionStart({
  packageName: "@theglitchking/babel-fish",
  pluginName: "babel-fish",
  configFile: "babel-fish.json",
});

mineVocabulary(process.cwd());

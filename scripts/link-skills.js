#!/usr/bin/env node
// Postinstall — delegates to @theglitchking/claude-plugin-runtime.
// babel-fish ships two skills (skills/babel-fish-developer-skill/ and
// skills/structure-bootstrap/) which the runtime symlinks into
// <project>/.claude/skills/ so Claude Code can discover them. Runtime also writes the default update-policy config
// and registers the SessionStart hook (with plugin-vs-npm dedup).
//
// NOTE: npm install only handles the skill + update policy. To get the
// full project-map infra (.claude/project-map/generate.py, the
// pre-commit hook, rules files), users still run:
//   npx @theglitchking/babel-fish init

import { runPostinstall } from "@theglitchking/claude-plugin-runtime";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

try {
  runPostinstall({
    packageName: "@theglitchking/babel-fish",
    pluginName: "babel-fish",
    configFile: "babel-fish.json",
    skillsDir: "skills",
    packageRoot,
    hookCommand:
      "node ./node_modules/@theglitchking/babel-fish/hooks/session-start.js",
  });
} catch (err) {
  console.warn(`[babel-fish] postinstall failed: ${err?.message || err}`);
}

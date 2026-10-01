// Builds dist/hopper-<version>.zip for the OpenAI plugin portal (platform.openai.com/plugins).
// The Claude directory reads the GitHub repo instead.
//
// The ZIP is an OpenAI build of the plugin folder, staged in dist/openai/:
// - evals/ stays out (development only);
// - skills lose `allowed-tools` (a Claude Code permission field) and any line that
//   points users to buying credits, which OpenAI's commerce rules don't allow;
// - everything else is copied as is.
import { execFileSync } from "node:child_process";
import { cpSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const plugin = join(root, "hopper");
const { version } = JSON.parse(readFileSync(join(plugin, "plugin.json"), "utf8"));
const stage = join(root, "dist", "openai");
const out = join(root, "dist", `hopper-${version}.zip`);

execFileSync("node", [join(root, "tools", "check.mjs")], { stdio: "inherit" });
rmSync(stage, { recursive: true, force: true });
mkdirSync(stage, { recursive: true });
cpSync(plugin, stage, {
  recursive: true,
  filter: (src) => !/[/\\](evals|__pycache__)([/\\]|$)/.test(src.slice(plugin.length)) && !src.endsWith(".DS_Store"),
});

const purchase = /top up|top-up|add credits|buy credits/i;
for (const skill of readdirSync(join(stage, "skills"))) {
  const path = join(stage, "skills", skill, "SKILL.md");
  const lines = readFileSync(path, "utf8").split("\n");
  const kept = lines.filter((line) => !/^allowed-tools:/.test(line) && !purchase.test(line));
  writeFileSync(path, kept.join("\n"));
}

rmSync(out, { force: true });
execFileSync("zip", ["-rqX", out, "."], { cwd: stage });
console.log(`wrote ${out.slice(root.length + 1)} (OpenAI build in dist/openai)`);

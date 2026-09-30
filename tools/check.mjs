// Checks the plugin against both directories' published rules before a release.
//
//   node tools/check.mjs
//
// Covers the Claude plugin directory's pre-submission checklist
// (claude.com/docs/plugins/pre-submission-checklist), OpenAI's listing limits
// (developers.openai.com/plugins/deploy/submission), and consistency between the
// two manifests. Then runs `claude plugin validate --strict` when Claude Code is installed.
import { execFileSync } from "node:child_process";
import { existsSync, lstatSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const plugin = join(root, "hopper");
const errors = [];
const fail = (message) => errors.push(message);
const json = (path) => JSON.parse(readFileSync(join(root, path), "utf8"));

const portable = json("hopper/plugin.json");
const claude = json("hopper/.claude-plugin/plugin.json");
const openai = portable.extensions?.["com.openai"] ?? {};
const ui = openai.interface ?? {};

// Identity: the name is permanent on both directories.
for (const [label, manifest] of [["plugin.json", portable], [".claude-plugin/plugin.json", claude]]) {
  if (manifest.name !== "hopper") fail(`${label}: name must stay "hopper"`);
  if (!/^\d+\.\d+\.\d+$/.test(manifest.version ?? "")) fail(`${label}: version must be x.y.z`);
  for (const key of ["description", "author", "license", "homepage", "repository"])
    if (!manifest[key]) fail(`${label}: missing ${key}`);
}
for (const key of ["version", "description", "license", "homepage", "repository"])
  if (JSON.stringify(portable[key]) !== JSON.stringify(claude[key])) fail(`manifests disagree on ${key}`);
if (claude.displayName !== ui.displayName) fail("manifests disagree on displayName");

// OpenAI listing limits.
const limits = { displayName: 30, shortDescription: 30, longDescription: 4000, developerName: 80 };
for (const [key, max] of Object.entries(limits)) {
  if (!ui[key]) fail(`interface.${key} is required`);
  else if (ui[key].length > max) fail(`interface.${key} is ${ui[key].length} chars (max ${max})`);
}
if (!Array.isArray(ui.defaultPrompt) || ui.defaultPrompt.length > 3) fail("defaultPrompt: up to 3 prompts");
for (const prompt of ui.defaultPrompt ?? []) if (prompt.length > 128) fail(`defaultPrompt over 128 chars: ${prompt}`);
if (new Set(ui.defaultPrompt).size !== (ui.defaultPrompt ?? []).length) fail("defaultPrompt entries must be unique");
for (const key of ["websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL"])
  if (!/^https:\/\/[^@\s]+$/.test(ui[key] ?? "")) fail(`interface.${key} must be an https URL`);
if (!/^#[0-9A-Fa-f]{6}$/.test(ui.brandColor ?? "")) fail("interface.brandColor must be #RRGGBB");
for (const key of ["composerIcon", "logo"]) {
  const path = ui[key];
  if (!path?.startsWith("./") || !existsSync(join(plugin, path))) {
    fail(`interface.${key} must be a ./ path that exists`);
    continue;
  }
  const png = readFileSync(join(plugin, path));
  const [w, h] = [png.readUInt32BE(16), png.readUInt32BE(20)];
  if (png.subarray(1, 4).toString() !== "PNG" || w !== h || w < 48 || w > 4096) fail(`${key}: square PNG, 48–4096 px`);
}
if (!existsSync(join(plugin, openai.onboardingSkill ?? "-"))) fail("onboardingSkill must exist");

// MCP: optional (the connector ships once withhopper.com/mcp is live). When present: one
// remote server, the same URL in both formats.
const hasMcp = existsSync(join(plugin, ".mcp.json"));
const mcpClaude = hasMcp ? json("hopper/.mcp.json").mcpServers : {};
if (hasMcp) {
  const mcpPortable = json("hopper/mcp.json").mcpServers;
  for (const [name, server] of Object.entries(mcpClaude)) {
    if (server.type !== "http" || !server.url?.startsWith("https://")) fail(`.mcp.json ${name}: type http, https url`);
    if (mcpPortable[name]?.type !== "streamable-http" || mcpPortable[name]?.url !== server.url)
      fail(`mcp.json ${name} must match .mcp.json (streamable-http, same url)`);
  }
  if (Object.keys(mcpClaude).join() !== Object.keys(mcpPortable).join()) fail("MCP server names differ between formats");
} else if (existsSync(join(plugin, "mcp.json"))) fail("mcp.json without .mcp.json");

// Marketplaces point at the plugin by the same name.
const ccMarket = json(".claude-plugin/marketplace.json");
const oaMarket = json(".agents/plugins/marketplace.json");
const ccEntry = ccMarket.plugins.find((p) => p.name === claude.name);
const oaEntry = oaMarket.plugins.find((p) => p.name === portable.name);
if (ccEntry?.source !== "./hopper") fail("Claude marketplace entry must point at ./hopper");
if (oaEntry?.source?.path !== "./hopper") fail("Codex marketplace entry must point at ./hopper");
for (const key of ["installation", "authentication"]) if (!oaEntry?.policy?.[key]) fail(`Codex marketplace: policy.${key}`);
if (!oaEntry?.category) fail("Codex marketplace: category");
const cursorEntry = json(".cursor-plugin/marketplace.json").plugins.find((p) => p.name === portable.name);
if (cursorEntry?.source !== "./hopper") fail("Cursor marketplace entry must point at ./hopper");

// MCP Registry listing: same server, same version.
const server = json("server.json");
if (hasMcp && server.remotes?.[0]?.url !== mcpClaude.hopper?.url) fail("server.json remote must match the plugin's MCP url");
if (server.version !== portable.version) fail("server.json version must match the plugin version");
if ((server.description ?? "").length > 100) fail("server.json description over 100 chars");

// hopper-announce: Claude Code only (hooks), so it's listed in the Claude marketplace alone.
const announce = json("hopper-announce/.claude-plugin/plugin.json");
if (ccMarket.plugins.find((p) => p.name === announce.name)?.source !== "./hopper-announce") fail("Claude marketplace must list hopper-announce");
if (oaMarket.plugins.some((p) => p.name === announce.name)) fail("hopper-announce uses hooks: keep it out of the Codex marketplace");

// Files: what the Claude directory blocks or holds.
const files = [];
function checkPlugin(plugin) {
const name0 = relative(root, plugin);
const before = files.length;
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    const rel = relative(plugin, path);
    if (rel === join("evals", "results") || name === "__pycache__") continue; // gitignored output
    if (/^(\.DS_Store|Thumbs\.db|desktop\.ini|__MACOSX)$/.test(name)) fail(`system file: ${rel}`);
    if (!/^[\w.-]+$/.test(name)) fail(`file name not portable: ${rel}`);
    const stat = lstatSync(path);
    if (stat.isSymbolicLink()) fail(`symlink: ${rel}`);
    else if (stat.isDirectory()) walk(path);
    else {
      files.push(rel);
      const image = /\.(png|jpe?g|gif|webp|svg)$/i.test(name);
      if (!image && stat.size > 256 * 1024) fail(`over 256 KiB: ${rel}`);
      if (stat.size > 5 * 1024 * 1024) fail(`over 5 MiB: ${rel}`);
      if (!image && !/\.(md|json|py|txt|yaml|yml|sh|mjs|js|toml)$|^LICENSE$|^\.gitignore$/.test(name)) fail(`unexpected file type: ${rel}`);
    }
  }
})(plugin);
if (files.length - before > 512) fail(`${name0}: ${files.length - before} files (max 512)`);
const lower = files.slice(before).map((f) => f.toLowerCase());
if (new Set(lower).size !== lower.length) fail("two file names differ only by case");

const readme = readFileSync(join(plugin, "README.md"), "utf8").replace(/```[\s\S]*?```/g, "");
if (readme.split(/\s+/).filter(Boolean).length < 40) fail(`${name0}: README under 40 words outside code blocks`);
if (!existsSync(join(plugin, "LICENSE"))) fail(`${name0}: LICENSE missing`);

// Skills: portable frontmatter, and every bundled path they name exists.
const portableKeys = new Set(["name", "description", "license", "compatibility", "metadata", "allowed-tools"]);
for (const skill of readdirSync(join(plugin, "skills"))) {
  const dir = join(plugin, "skills", skill);
  const text = readFileSync(join(dir, "SKILL.md"), "utf8");
  const front = text.match(/^---\n([\s\S]*?)\n---\n/);
  if (!front) {
    fail(`${name0}/skills/${skill}: no frontmatter`);
    continue;
  }
  const fields = Object.fromEntries(
    front[1].split("\n").map((line) => {
      const value = line.slice(line.indexOf(":") + 1).trim();
      const quoted = value.match(/^'(.*)'$/);
      return [line.slice(0, line.indexOf(":")), quoted ? quoted[1].replaceAll("''", "'") : value];
    }),
  );
  if (/^description: [^'"].*: /m.test(front[1])) fail(`${name0}/skills/${skill}: quote the description (it contains ": ")`);
  for (const key of Object.keys(fields)) if (!portableKeys.has(key)) fail(`${name0}/skills/${skill}: non-portable key ${key}`);
  if (fields.name !== skill) fail(`${name0}/skills/${skill}: name must match the folder`);
  if (!fields.description || fields.description.length > 1024) fail(`${name0}/skills/${skill}: description 1–1024 chars`);
  if (/\bcurl\b|\bwget\b/.test(text)) fail(`${name0}/skills/${skill}: downloads at run time`);
  for (const [, path] of text.matchAll(/\$\{CLAUDE_SKILL_DIR\}\/([\w./-]+\.(?:py|md))/g))
    if (!existsSync(join(dir, path))) fail(`${name0}/skills/${skill}: ${path} doesn't exist`);
  for (const [, name] of text.matchAll(/`(\w[\w-]*\.md)`/g))
    if (name !== "SKILL.md" && !existsSync(join(dir, "references", name)) && !existsSync(join(dir, name)))
      fail(`${name0}/skills/${skill}: ${name} doesn't exist`);
}
}
checkPlugin(plugin);
checkPlugin(join(root, "hopper-announce"));

if (errors.length) {
  for (const message of errors) console.error(`✗ ${message}`);
  process.exit(1);
}
console.log(`✔ plugin checks passed (${files.length} files)`);

try {
  execFileSync("claude", ["--version"], { stdio: "ignore" });
} catch {
  console.log("claude not installed: skipped `claude plugin validate`");
  process.exit(0);
}
for (const target of [plugin, join(root, "hopper-announce"), root]) execFileSync("claude", ["plugin", "validate", "--strict", target], { stdio: "inherit" });

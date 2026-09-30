// Builds dist/hopper-inference-<version>.zip for the OpenAI plugin portal
// (platform.openai.com/plugins). The Claude directory reads the GitHub repo instead.
// Evals stay out of the ZIP: they're for development, not for the listing.
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const plugin = join(root, "hopper-inference");
const { version } = JSON.parse(readFileSync(join(plugin, "plugin.json"), "utf8"));
const out = join(root, "dist", `hopper-inference-${version}.zip`);
execFileSync("node", [join(root, "tools", "check.mjs")], { stdio: "inherit" });
mkdirSync(dirname(out), { recursive: true });
rmSync(out, { force: true });
execFileSync("zip", ["-rqX", out, ".", "-x", "evals/*", "*.DS_Store"], { cwd: plugin });
console.log(`wrote ${out.slice(root.length + 1)}`);

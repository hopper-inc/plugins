// The scripts and framework pages are published at https://withhopper.com/agents/ and
// tested there (frontend repo: public/agents/, scripts/verify-agent-pages.py). This
// plugin bundles copies so nothing is downloaded at run time.
//
//   node tools/sync.mjs            download the published files into the plugin
//   node tools/sync.mjs --check    exit 1 if a bundled copy differs from the published one
//   node tools/sync.mjs --from <frontend checkout>   copy from public/agents/ instead
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const plugin = resolve(dirname(fileURLToPath(import.meta.url)), "..", "hopper-inference");
// Each skill carries its own copy, so it still works when a host installs one skill
// folder on its own (npx skills, claude.ai skill uploads).
const files = [
  ["hopper_trial.py", "skills/integrate/scripts"],
  ["hopper_claim.py", "skills/integrate/scripts"],
  ["hopper_ttft.py", "skills/integrate/scripts"],
  ["hopper_trial.py", "skills/benchmark/scripts"],
  ["hopper_ttft.py", "skills/benchmark/scripts"],
  ...["livekit.md", "pipecat.md", "vapi.md", "openai-sdk.md"].flatMap((page) => [
    [page, "skills/integrate/references"],
    [page, "skills/diagnose/references"],
  ]),
];
const fromIndex = process.argv.indexOf("--from");
const from = fromIndex > 0 ? process.argv[fromIndex + 1] : null;

async function published(name) {
  if (from) return readFileSync(join(from, "public", "agents", name), "utf8");
  const response = await fetch(`https://withhopper.com/agents/${name}`);
  if (!response.ok) throw new Error(`${name}: HTTP ${response.status}`);
  return response.text();
}

const check = process.argv.includes("--check");
let drifted = 0;
const cache = {};
for (const [name, folder] of files) {
  const path = join(plugin, folder, name);
  const want = cache[name] ??= await published(name);
  if (check) {
    let have = "";
    try {
      have = readFileSync(path, "utf8");
    } catch {}
    if (have !== want) {
      drifted++;
      console.error(`out of date: hopper-inference/${folder}/${name}`);
    }
  } else {
    writeFileSync(path, want);
  }
}
if (check && drifted) {
  console.error("run: node tools/sync.mjs");
  process.exit(1);
}
console.log(check ? `in sync with ${from ?? "withhopper.com"} (${files.length} files)` : `synced ${files.length} files`);

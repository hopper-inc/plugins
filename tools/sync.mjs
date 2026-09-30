// The scripts and framework pages are published at https://withhopper.com/agents/ and
// tested there (frontend repo: public/agents/, scripts/verify-agent-pages.py). This
// plugin bundles copies so nothing is downloaded at run time.
//
//   node tools/sync.mjs            download the published files into the plugin
//   node tools/sync.mjs --check    exit 1 if a bundled copy differs from the published one
//   node tools/sync.mjs --from <frontend checkout>   copy from public/agents/ instead
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const plugin = resolve(dirname(fileURLToPath(import.meta.url)), "..", "hopper-inference");
// Each skill carries its own copy, so it still works when a host installs one skill
// folder on its own (npx skills, claude.ai skill uploads).
const files = [
  ["hopper_trial.py", "skills/hopper-integrate/scripts"],
  ["hopper_claim.py", "skills/hopper-integrate/scripts"],
  ["hopper_ttft.py", "skills/hopper-integrate/scripts"],
  ["hopper_trial.py", "skills/hopper-benchmark/scripts"],
  ["hopper_ttft.py", "skills/hopper-benchmark/scripts"],
  ...["livekit.md", "pipecat.md", "vapi.md", "openai-sdk.md"].flatMap((page) => [
    [page, "skills/hopper-integrate/references"],
    [page, "skills/hopper-diagnose/references"],
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
// Files that originate in this repo and are shared between skills: the first path is
// the source, the rest are copies.
const local = [["skills/hopper-speak/scripts/hopper_voice.py", "skills/hopper-transcribe/scripts/hopper_voice.py", "../hopper-announce/scripts/hopper_voice.py"]];
for (const [source, ...copies] of local) {
  const want = readFileSync(join(plugin, source), "utf8");
  for (const copy of copies) {
    const path = join(plugin, copy);
    if (check) {
      let have = "";
      try {
        have = readFileSync(path, "utf8");
      } catch {}
      if (have !== want) {
        drifted++;
        console.error(`out of date: hopper-inference/${copy} (source: ${source})`);
      }
    } else {
      mkdirSync(dirname(path), { recursive: true });
      writeFileSync(path, want);
    }
  }
}
// .codex-plugin/plugin.json: the layout every plugin in openai/plugins uses, generated from
// plugin.json (Codex prefers the inline extensions.com.openai when both exist).
{
  const portable = JSON.parse(readFileSync(join(plugin, "plugin.json"), "utf8"));
  const { review, publication, onboardingSkill, ...openai } = portable.extensions["com.openai"];
  const codex = {
    name: portable.name,
    version: portable.version,
    description: portable.description,
    author: portable.author,
    homepage: portable.homepage,
    repository: portable.repository,
    license: portable.license,
    keywords: portable.keywords,
    skills: "./skills/",
    mcpServers: "./.mcp.json",
    ...openai,
  };
  const want = JSON.stringify(codex, null, 2) + "\n";
  const path = join(plugin, ".codex-plugin", "plugin.json");
  if (check) {
    let have = "";
    try {
      have = readFileSync(path, "utf8");
    } catch {}
    if (have !== want) {
      drifted++;
      console.error("out of date: hopper-inference/.codex-plugin/plugin.json (generated from plugin.json)");
    }
  } else {
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, want);
  }
}
if (check && drifted) {
  console.error("run: node tools/sync.mjs");
  process.exit(1);
}
console.log(check ? `in sync with ${from ?? "withhopper.com"} (${files.length} files)` : `synced ${files.length} files`);

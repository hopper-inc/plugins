// Builds claude-directory/hopper, the plugin submitted to Claude's plugin directory,
// from hopper/. The directory doesn't list software that generates audio (Anthropic
// Software Directory Policy 4B), so this copy has no text to speech: no hopper-speak
// skill, no speak code in the transcribe script, and its connector is
// https://withhopper.com/mcp/claude (the server without speak and list_voices).
//
//   node tools/directory.mjs           regenerate claude-directory/hopper
//   node tools/directory.mjs --check   exit 1 if the committed copy is out of date
//
// Each edit below names the exact text it replaces and stops if that text is gone,
// so a change in hopper/ that this copy needs to follow fails loudly.
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = join(root, "hopper");
const target = join(root, "claude-directory", "hopper");
const check = process.argv.includes("--check");

const SKILLS = ["hopper-integrate", "hopper-transcribe", "hopper-try"];
const MCP_URL = "https://withhopper.com/mcp/claude";
const DESCRIPTION =
  "Realtime inference API for open-source models in your agent: two LLMs and speech-to-text. Try the latest open-source models on your own prompts, add a key to your code, and transcribe audio.";

const read = (path) => readFileSync(join(source, path), "utf8");

function replace(text, from, to, where) {
  if (!text.includes(from)) throw new Error(`${where}: expected text not found, update tools/directory.mjs:\n${from}`);
  return text.split(from).join(to);
}

// Removes the lines from the one starting with `start` up to, not including, the one starting with `end`.
function cut(text, start, end, where) {
  const lines = text.split("\n");
  const from = lines.findIndex((line) => line.startsWith(start));
  const to = lines.findIndex((line, i) => i > from && line.startsWith(end));
  if (from < 0 || to < 0) throw new Error(`${where}: section ${start} … ${end} not found, update tools/directory.mjs`);
  return [...lines.slice(0, from), ...lines.slice(to)].join("\n");
}

const files = new Map();

// Manifest: same identity, description without text to speech.
{
  const manifest = JSON.parse(read(".claude-plugin/plugin.json"));
  manifest.description = DESCRIPTION;
  manifest.keywords = manifest.keywords.filter((k) => !["text to speech", "tts"].includes(k));
  manifest.privacyPolicyUrl = "https://withhopper.com/privacy";
  files.set(".claude-plugin/plugin.json", `${JSON.stringify(manifest, null, 2)}\n`);
}

files.set(".mcp.json", `${JSON.stringify({ mcpServers: { hopper: { type: "http", url: MCP_URL } } }, null, 2)}\n`);
files.set("LICENSE", read("LICENSE"));

// Skills, copied as they are, except where they point at hopper-speak.
const walk = (dir) =>
  readdirSync(join(source, dir)).flatMap((name) => {
    const path = join(dir, name);
    if (name === "__pycache__" || name === ".DS_Store") return [];
    return statSync(join(source, path)).isDirectory() ? walk(path) : [path];
  });
for (const skill of SKILLS) for (const path of walk(join("skills", skill))) files.set(path, read(path));

const edit = (path, ...pairs) => {
  let text = files.get(path);
  for (let i = 0; i < pairs.length; i += 2) text = replace(text, pairs[i], pairs[i + 1], path);
  files.set(path, text);
};

edit(
  "skills/hopper-try/SKILL.md",
  "or audio (the `hopper-speak` and `hopper-transcribe` skills: Qwen 3 TTS and Nemotron ASR)",
  "or transcription (the `hopper-transcribe` skill: Nemotron ASR)",
);
edit("skills/hopper-transcribe/SKILL.md", "Not for generating audio (hopper-speak) or running an LLM (hopper-try).", "Not for running an LLM (hopper-try).");
edit(
  "skills/hopper-integrate/SKILL.md",
  "Not for trying or comparing models before deciding (hopper-try), speech or transcription (hopper-speak, hopper-transcribe), or running models locally.",
  "Not for trying or comparing models before deciding (hopper-try), transcription (hopper-transcribe), or running models locally.",
);

// The transcribe script without its text-to-speech commands.
{
  const path = "skills/hopper-transcribe/scripts/hopper_voice.py";
  edit(
    path,
    `"""Hopper text to speech and speech to text for an agent's own use.

    python3 hopper_voice.py speak "Text to say" [--voice elena] [--out speech.wav] [--play]
    python3 hopper_voice.py speak --file notes.md [--out notes.wav]
    python3 hopper_voice.py transcribe recording.m4a [--json]
    python3 hopper_voice.py voices
`,
    `"""Hopper speech to text for an agent's own use.

    python3 hopper_voice.py transcribe recording.m4a [--json]
`,
    `TTS_MODEL, TTS_LIMIT = "qwen3-tts", 1000  # characters per request\n`,
    "",
    `ap = argparse.ArgumentParser(description="Hopper text to speech and speech to text")`,
    `ap = argparse.ArgumentParser(description="Hopper speech to text")`,
    `    sub.add_parser("voices", help="list ready voices").set_defaults(
        run=lambda _: print(json.dumps([{"id": v["id"], "description": v.get("description"), "gender": v.get("gender"), "tags": v.get("tags")} for v in list_voices()], indent=1))
    )
`,
    "",
  );
  let text = files.get(path);
  text = cut(text, "# --- voices", "# --- transcribe", path);
  text = cut(text, '    s = sub.add_parser("speak"', '    t = sub.add_parser("transcribe"', path);
  for (const gone of ["/v1/audio/speech", "def speak", "TTS_MODEL", "list_voices"]) {
    if (text.includes(gone)) throw new Error(`${path}: still contains ${gone}`);
  }
  files.set(path, text);
}

files.set(
  "README.md",
  `# Hopper

Realtime inference API for open-source models in your agent: DeepSeek V4.1 Flash (\`deepseek-v4.1-flash\`) and Gemma 4 31B (\`gemma-4-31b\`) for text, and Nemotron ASR (\`nemotron-asr\`) for transcription, behind an OpenAI-compatible API at \`https://api.withhopper.com/v1\`. Test the models on your own prompts, then put a key in your code.

## Skills

| Skill | Ask | What it does |
| --- | --- | --- |
| \`hopper-try\` | "Try the new DeepSeek on this prompt" | Runs your prompts, system prompt and tool definitions on Hopper's LLMs side by side, with time to first token, tokens per second and cost. Changes no files. |
| \`hopper-integrate\` | "Switch this app to DeepSeek on Hopper" | Gets the project a key, shows the planned change, and after you say go points the project's OpenAI-compatible client at a Hopper model: OpenAI SDK (Python or JavaScript), LangChain, Vercel AI SDK, LiteLLM, raw HTTP, LiveKit Agents, Pipecat or Vapi. Voice agents also get a time-to-first-token run on their own prompt. |
| \`hopper-transcribe\` | "What does this recording say?" | Speech to text with Nemotron ASR for audio or video files (WAV, MP3, M4A, voice memos, MP4), with word timestamps. |

## Connector

The plugin connects Claude to Hopper's MCP server at \`${MCP_URL}\`.

| Tool | Sign-in | What it does |
| --- | --- | --- |
| \`generate\` | No | Runs a prompt on one or more of Hopper's LLMs, with time to first token, tokens per second and cost |
| \`transcribe\` | No | Speech to text with word timestamps, from an audio URL or base64 audio |
| \`list_models\` | No | Models, context lengths and prices |
| \`get_integration_guide\` | No | Client code for the OpenAI SDK, LiveKit Agents, Pipecat or Vapi |
| \`get_account\` | Yes | Credits, usage and API key names (never key secrets) |
| \`create_api_key\` | Yes | Creates a key; the secret opens once in the Hopper console |

\`generate\` and \`transcribe\` work without an account within daily limits. Signing in uses OAuth with your Hopper account, and usage is then billed to it.

## What it runs and sends

Everything the skills run is readable Python in their \`scripts/\` folders: standard library only, plus the \`openai\` and \`h2\` packages for the voice-agent benchmark and \`ffmpeg\` to decode compressed audio.

- **\`hopper_try.py\`** (try) sends the prompts, system prompt and tool definitions you test to \`https://api.withhopper.com/v1/chat/completions\`, once per model, streamed. It uses \`HOPPER_API_KEY\` or the project's \`.env\` if present; otherwise it registers a trial key through Hopper's agent registration (\`https://withhopper.com/auth.md\`) and keeps it in \`~/.config/hopper/\` (mode 600), never in the project. It changes no files in the project.
- **\`hopper_trial.py\`**, **\`hopper_claim.py\`** (integrate) register a trial key for the project the same way, and move it to your Hopper account when you ask.
- **\`hopper_ttft.py\`** (integrate, voice agents) reads \`HOPPER_API_KEY\` and sends the agent's system prompt, its tool definitions and ten scripted caller turns to \`https://api.withhopper.com/v1/chat/completions\`. About $0.01–0.02 of credit per run.
- **\`hopper_voice.py\`** (transcribe) sends the audio to transcribe to \`https://api.withhopper.com/v1/audio/transcriptions\`, with the same key lookup and trial registration as \`hopper_try.py\`. Its \`claim\` command moves the trial key to your account.
- **\`hopper-integrate\`** runs \`pip install openai h2\` in the project's virtualenv for a voice-agent benchmark, and after your go edits the file that builds the LLM client.

Keys are never printed. Text and audio you send go to Hopper's API. Privacy policy: https://withhopper.com/privacy. Terms: https://withhopper.com/terms. Support: founders@withhopper.com.

## License

MIT
`,
);

// Write, or compare with what's committed.
let drifted = 0;
const existing = existsSync(target)
  ? (function list(dir) {
      return readdirSync(dir).flatMap((name) => {
        const path = join(dir, name);
        return statSync(path).isDirectory() ? list(path) : [relative(target, path)];
      });
    })(target)
  : [];
if (check) {
  for (const [path, text] of files) {
    const full = join(target, path);
    if (!existsSync(full) || readFileSync(full, "utf8") !== text) {
      drifted++;
      console.error(`out of date: claude-directory/hopper/${path}`);
    }
  }
  for (const path of existing) {
    if (!files.has(path)) {
      drifted++;
      console.error(`not generated: claude-directory/hopper/${path}`);
    }
  }
  if (drifted) {
    console.error("run: node tools/directory.mjs");
    process.exit(1);
  }
  console.log(`claude-directory/hopper is up to date (${files.size} files)`);
} else {
  rmSync(target, { recursive: true, force: true });
  for (const [path, text] of files) {
    mkdirSync(dirname(join(target, path)), { recursive: true });
    writeFileSync(join(target, path), text);
  }
  console.log(`wrote claude-directory/hopper (${files.size} files)`);
}

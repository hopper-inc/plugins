// Runs the plugin's eval cases in Claude Code or Codex, under your normal login.
//
//   node tools/run-evals.mjs --host claude|codex [--tag offline] [--case diagnose-slow] [--runs 1] [--baseline]
//
// `claude plugin eval` is the reference harness for Claude Code, but its runs start in a
// sealed home and need CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY; Codex has no eval
// command at all. This runner reads the same cases (evals/<case>/{case.yaml,prompt.md,
// scaffold.sh,graders/}) and, per run: scaffolds a temp workspace, runs the host with only
// this plugin loaded (--baseline: without it), and scores the graders. `llm` graders are
// judged by `claude -p` (one vote); set --judge none to skip them.
import { execFileSync, spawn } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const plugin = join(root, "hopper");
const evals = join(plugin, "evals");
const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > 0 ? process.argv[i + 1] : fallback;
};
const host = arg("host", "claude");
const tag = arg("tag", "offline");
const only = arg("case");
const runs = Number(arg("runs", "1"));
const judgeModel = arg("judge", "sonnet");
const baseline = process.argv.includes("--baseline");
const concurrency = Number(arg("j", "3"));

const frontmatter = (text) => {
  const m = text.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!m) return [{}, text];
  const fields = {};
  for (const line of m[1].split("\n")) {
    const i = line.indexOf(":");
    if (i > 0) fields[line.slice(0, i).trim()] = line.slice(i + 1).trim().replace(/^'(.*)'$/, "$1");
  }
  return [fields, m[2]];
};

function run(cmd, args, options) {
  return new Promise((done) => {
    const child = spawn(cmd, args, { ...options, stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    child.stdout.on("data", (chunk) => (stdout += chunk));
    child.stderr.on("data", () => {});
    const timer = setTimeout(() => child.kill("SIGTERM"), options.timeout);
    child.on("close", (code) => {
      clearTimeout(timer);
      done({ code, stdout });
    });
  });
}

const jsonLines = (text) =>
  text.split("\n").flatMap((line) => {
    try {
      return [JSON.parse(line)];
    } catch {
      return [];
    }
  });

let codexEnv;
function codexHome() {
  if (codexEnv) return codexEnv;
  const home = mkdtempSync(join(tmpdir(), "codex-eval-home-"));
  copyFileSync(join(homedir(), ".codex", "auth.json"), join(home, "auth.json"));
  codexEnv = { ...process.env, CODEX_HOME: home };
  if (!baseline) {
    execFileSync("codex", ["plugin", "marketplace", "add", root], { env: codexEnv, stdio: "ignore" });
    execFileSync("codex", ["plugin", "add", "hopper@hopper"], { env: codexEnv, stdio: "ignore" });
  }
  return codexEnv;
}

// Normalizes a host transcript to { reply, skills[], commands[], edits }.
async function execute(prompt, workspace, timeout, maxTurns) {
  const runEnv = { HOPPER_CONFIG_DIR: `${workspace}.hopper-config` };
  mkdirSync(runEnv.HOPPER_CONFIG_DIR, { mode: 0o700 });
  if (host === "codex") {
    const { stdout } = await run(
      "codex",
      ["exec", "--json", "--skip-git-repo-check", "-s", "workspace-write", "-c", "sandbox_workspace_write.network_access=true", "--add-dir", runEnv.HOPPER_CONFIG_DIR, prompt],
      { cwd: workspace, env: { ...codexHome(), ...runEnv }, timeout },
    );
    const events = jsonLines(stdout).filter((e) => e.type === "item.completed");
    const commands = events.filter((e) => e.item?.type === "command_execution").map((e) => e.item.command);
    return {
      trace: stdout,
      reply: events.filter((e) => e.item?.type === "agent_message").at(-1)?.item.text ?? "",
      // Codex has no Skill tool: a skill is used when its SKILL.md is read.
      skills: commands.flatMap((c) => [...c.matchAll(/skills\/([\w-]+)\/SKILL\.md/g)].map((m) => m[1])),
      commands,
      edits: events.filter((e) => e.item?.type === "file_change").length,
    };
  }
  const args = ["-p", prompt, "--output-format", "stream-json", "--verbose", "--allowedTools", "Bash Read Write Edit Glob Grep Skill"];
  if (!baseline) args.push("--plugin-dir", plugin);
  if (maxTurns) args.push("--max-turns", String(maxTurns));
  const { stdout } = await run("claude", args, { cwd: workspace, env: { ...process.env, ...runEnv }, timeout });
  const uses = jsonLines(stdout)
    .filter((e) => e.type === "assistant")
    .flatMap((e) => e.message.content.filter((c) => c.type === "tool_use"));
  const result = jsonLines(stdout).find((e) => e.type === "result");
  return {
    trace: stdout,
    reply: result?.result ?? "",
    skills: uses.filter((u) => u.name === "Skill").map((u) => u.input.skill.replace(/^[\w-]+:/, "")),
    commands: uses.filter((u) => u.name === "Bash").map((u) => u.input.command),
    edits: uses.filter((u) => u.name === "Edit" || u.name === "Write").length,
    cost: result?.total_cost_usd,
  };
}

async function judge(criteria, content) {
  const prompt = `You are grading an AI coding agent's work against a rubric. Think it through briefly, then end with one final line: VERDICT: PASS or VERDICT: FAIL.\n\n<rubric>\n${criteria}\n</rubric>\n\n<work>\n${content.slice(-60000)}\n</work>`;
  const { stdout } = await run("claude", ["-p", prompt, "--model", judgeModel, "--tools", ""], {
    cwd: tmpdir(),
    env: process.env,
    timeout: 180_000,
  });
  const verdicts = [...stdout.matchAll(/VERDICT:\s*(PASS|FAIL)/g)];
  const pass = verdicts.at(-1)?.[1] === "PASS";
  const reason = stdout.replace(/VERDICT:\s*(PASS|FAIL)/g, "").trim().split("\n").filter(Boolean).at(-1) ?? "";
  return [pass, pass ? "" : reason.slice(0, 200)];
}

const within = (n, g) => n >= Number(g.min ?? 1) && n <= Number(g.max ?? Infinity);

async function grade(dir, workspace, t) {
  const results = [];
  for (const file of readdirSync(join(dir, "graders")).sort()) {
    const [g, body] = frontmatter(readFileSync(join(dir, "graders", file), "utf8"));
    const name = file.replace(/\.md$/, "");
    const path = ((g.target ?? g.focus ?? "").match(/path:\s*([^\s}]+)/) ?? [])[1];
    const text =
      g.target === "trace" ? t.trace : path ? (existsSync(join(workspace, path)) ? readFileSync(join(workspace, path), "utf8") : "") : t.reply;
    if (g.type === "regex") {
      const found = new RegExp(g.pattern, g.flags ?? "").test(text);
      results.push([name, g.match === "not_contains" ? !found : found]);
    } else if (g.type === "tool_used" && g.tool === "Skill") {
      const exact = (g.input_match ?? "").match(/\)\?([\w|-]+)"?/)?.[1];
      const want = exact ? new RegExp(`^(?:${exact})$`) : new RegExp(g.input_match ?? ".");
      if (baseline && g.max === undefined) continue; // with-only: there's no plugin to fire
      results.push([name, within(t.skills.filter((s) => want.test(s)).length, g)]);
    } else if (g.type === "tool_used" && g.tool === "Bash") {
      results.push([name, within(t.commands.filter((c) => new RegExp(g.input_match ?? ".").test(c)).length, g)]);
    } else if (g.type === "tool_used" && (g.tool === "Edit" || g.tool === "Write")) {
      results.push([name, within(t.edits, g)]);
    } else if (g.type === "file_exists") {
      const exists = existsSync(join(workspace, g.path));
      results.push([name, g.exists === "false" ? !exists : exists]);
    } else if (g.type === "llm") {
      if (judgeModel === "none") results.push([name, null, "judge skipped"]);
      else results.push([name, ...(await judge(body.trim(), text))]);
    } else results.push([name, null, `unsupported grader ${g.type}`]);
  }
  return results;
}

// --triggers: which skill loads for each prompt in evals/triggers.json (null = none should).
// Runs stop early (Claude --max-turns 2, Codex after the timeout); only the skill choice is scored.
if (process.argv.includes("--triggers")) {
  const prompts = JSON.parse(readFileSync(join(evals, "triggers.json"), "utf8"));
  const queue = prompts.map((p, i) => [p, i]);
  const rows = [];
  await Promise.all(
    Array.from({ length: concurrency }, async () => {
      while (queue.length) {
        const [p, i] = queue.shift();
        const workspace = mkdtempSync(join(tmpdir(), `trigger-${host}-`));
        execFileSync("bash", [join(evals, "_triggers-scaffold.sh")], { cwd: workspace, stdio: "ignore" });
        const t = await execute(p.prompt, workspace, 90_000, 2);
        const fired = [...new Set(t.skills.filter((s) => s.startsWith("hopper-")))];
        const ok = p.skill ? fired.length === 1 && fired[0] === p.skill : fired.length === 0;
        rows[i] = { ...p, fired, ok };
        console.log(`${ok ? "✓" : "✗"} ${p.skill ?? "(none)"} ← "${p.prompt}"${ok ? "" : `  fired: ${fired.join(", ") || "nothing"}`}`);
      }
    }),
  );
  const pos = rows.filter((r) => r.skill);
  const neg = rows.filter((r) => !r.skill);
  console.log(`\nrecall ${pos.filter((r) => r.ok).length}/${pos.length} · clean negatives ${neg.filter((r) => r.ok).length}/${neg.length}`);
  process.exit(rows.every((r) => r.ok) ? 0 : 1);
}

const cases = readdirSync(evals)
  .filter((name) => existsSync(join(evals, name, "case.yaml")))
  .filter((name) => (only ? name === only : new RegExp(`\\b${tag}\\b`).test(readFileSync(join(evals, name, "case.yaml"), "utf8"))));
const jobs = cases.flatMap((name) => Array.from({ length: runs }, (_, i) => [name, i + 1]));

async function job([name, n]) {
  const dir = join(evals, name);
  const [meta, prompt] = frontmatter(readFileSync(join(dir, "prompt.md"), "utf8"));
  const workspace = mkdtempSync(join(tmpdir(), `eval-${host}-${name}-`));
  execFileSync("bash", [join(dir, "scaffold.sh")], { cwd: workspace, stdio: "ignore" });
  const started = Date.now();
  const t = await execute(prompt.trim(), workspace, Number(meta.timeout_seconds ?? 600) * 1000);
  writeFileSync(`${workspace}.trace.jsonl`, t.trace);
  writeFileSync(`${workspace}.reply.md`, t.reply);
  const results = await grade(dir, workspace, t);
  const scored = results.filter(([, pass]) => pass !== null);
  const score = scored.filter(([, pass]) => pass).length / (scored.length || 1);
  const lines = [
    `${score === 1 ? "✓" : "✗"} ${name} #${n} [${host}${baseline ? ", no plugin" : ""}] ${score.toFixed(2)} · ${((Date.now() - started) / 1000).toFixed(0)}s${t.cost ? ` · $${t.cost.toFixed(2)}` : ""} · ${workspace}`,
    ...results.map(([g, pass, why]) => `    ${pass === null ? "·" : pass ? "✓" : "✗"} ${g}${why ? ` — ${why}` : ""}`),
  ];
  console.log(lines.join("\n"));
  return score;
}

const scores = [];
const queue = [...jobs];
await Promise.all(
  Array.from({ length: Math.min(concurrency, queue.length) }, async () => {
    while (queue.length) scores.push(await job(queue.shift()));
  }),
);
const mean = scores.reduce((a, b) => a + b, 0) / (scores.length || 1);
console.log(`\n${scores.length} runs · mean ${mean.toFixed(2)} · ${scores.filter((s) => s === 1).length} perfect`);
process.exit(scores.every((s) => s === 1) ? 0 : 1);

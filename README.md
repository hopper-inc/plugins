# Hopper plugins

Plugins for [Hopper](https://withhopper.com): fast open-source LLM inference for voice agents.

| Plugin | What it does |
| :--- | :--- |
| [`hopper-inference`](hopper-inference/) | The fastest LLM for voice agents, and a voice and ears for any agent: set Hopper up in a voice-agent project, benchmark and diagnose time to first token, speak text and transcribe recordings. Skills that call Hopper's API directly. |
| [`hopper-announce`](hopper-announce/) | Claude Code says out loud when a long task finishes. Claude Code only (hooks). |

## Install

| Host | Command |
| :--- | :--- |
| Claude Code | `claude plugin marketplace add hopper-inc/plugins` then `claude plugin install hopper-inference@hopper` (and `hopper-announce@hopper`) |
| Codex | `codex plugin marketplace add hopper-inc/plugins` then `codex plugin add hopper-inference@hopper` |
| Cursor, VS Code / Copilot | Add the marketplace `hopper-inc/plugins` |
| Any agent that reads Agent Skills | `npx skills add hopper-inc/plugins` |

No plugin? Paste this into your coding agent:

```text
Set up Hopper in this project using https://withhopper.com/skill.md
```

## Layout

```
.claude-plugin/marketplace.json      Claude Code marketplace
.agents/plugins/marketplace.json     Codex marketplace
.cursor-plugin/marketplace.json      Cursor marketplace
server.json                          MCP Registry listing (com.withhopper/hopper), for when the connector ships
hopper-inference/
  .claude-plugin/plugin.json         Claude Code manifest
  plugin.json                        Agent Plugins manifest + OpenAI listing (Codex, ChatGPT, Cursor, Copilot)
  skills/<skill>/                    hopper-{integrate,benchmark,diagnose,speak,transcribe}, each self-contained:
    scripts/ · references/           copies of https://withhopper.com/agents/*
  .codex-plugin/plugin.json          Codex layout, generated from plugin.json by tools/sync.mjs
  evals/                             eval cases with fixture projects; triggers.json for skill collisions
hopper-announce/                     Claude Code plugin: two hooks + one settings skill
tools/
  check.mjs                          directory rules + manifest consistency + claude plugin validate
  sync.mjs                           refresh the skills' scripts/ and references/ from withhopper.com
  run-evals.mjs                      run the eval cases in Claude Code or Codex under your own login
  package.mjs                        dist/hopper-inference-<version>.zip for the OpenAI plugin portal
```

## Develop

```bash
node tools/check.mjs                                  # before every commit
node tools/sync.mjs --check                           # bundled copies match the published ones
claude --plugin-dir hopper-inference                  # try it in Claude Code
claude plugin eval hopper-inference --tag offline --scaffold --trust-plugin --allow-tools Bash Write Edit
node tools/run-evals.mjs --host codex --tag offline   # the same cases in Codex (or --host claude)
node tools/run-evals.mjs --host claude --triggers      # which skill loads for 21 prompts, including ones that should load none
```

`--tag live` cases register a real trial key and call the production API; run them before a release, not in a loop.

Bump `version` in the manifests and `server.json` for every release and add a CHANGELOG entry; `tools/check.mjs` fails if the versions differ. Pick one install path per machine: the plugin or `npx skills`, not both.

## License

MIT

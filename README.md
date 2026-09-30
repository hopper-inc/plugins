# Hopper plugins

Plugins for [Hopper](https://withhopper.com): fast open-source LLM inference for voice agents.

| Plugin | What it does |
| :--- | :--- |
| [`hopper-inference`](hopper-inference/) | Sets Hopper up in a voice-agent project, benchmarks time to first token on the agent's own prompt, and finds what slows it down. Skills plus the Hopper MCP connector. |

## Install

| Host | Command |
| :--- | :--- |
| Claude Code | `claude plugin marketplace add hopper-inc/plugins` then `claude plugin install hopper-inference@hopper` |
| Codex | `codex plugin marketplace add hopper-inc/plugins` then `codex plugin add hopper-inference@hopper` |
| Cursor, VS Code / Copilot | Add the marketplace `hopper-inc/plugins` |
| Any agent that reads Agent Skills | `npx skills add hopper-inc/plugins` |
| Any MCP client | `https://withhopper.com/mcp` (Streamable HTTP) |

No plugin? Paste this into your coding agent:

```text
Set up Hopper in this project using https://withhopper.com/skill.md
```

## Layout

```
.claude-plugin/marketplace.json      Claude Code marketplace
.agents/plugins/marketplace.json     Codex marketplace
.cursor-plugin/marketplace.json      Cursor marketplace
server.json                          MCP Registry listing (com.withhopper/hopper)
hopper-inference/
  .claude-plugin/plugin.json         Claude Code manifest
  plugin.json                        Agent Plugins manifest + OpenAI listing (Codex, ChatGPT, Cursor, Copilot)
  .mcp.json · mcp.json               the Hopper MCP server, in each format
  skills/<skill>/                    integrate · benchmark · diagnose, each self-contained:
    scripts/ · references/           copies of https://withhopper.com/agents/*
  evals/                             eval cases with fixture projects
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
```

`--tag live` cases register a real trial key and call the production API; run them before a release, not in a loop.

Bump `version` in both manifests and `server.json` for every release; `tools/check.mjs` fails if they differ.

## License

MIT

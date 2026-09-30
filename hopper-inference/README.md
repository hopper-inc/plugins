# Hopper

Hopper serves open-source LLMs behind an OpenAI-compatible API built for real-time voice. This plugin lets a coding agent set Hopper up in an existing voice-agent project, measure time to first token on the agent's own prompt, and find what makes responses start late. It works in Claude Code, Codex, ChatGPT and Claude.

## Skills

| Skill | What it does |
| :--- | :--- |
| `integrate` | Gets a trial key ($2 credit, no sign-up), benchmarks a 10-turn simulated call on the agent's system prompt and tools, shows the results, and after you say go switches only the LLM in LiveKit Agents, Pipecat, Vapi or OpenAI SDK code. STT, TTS and tools stay as they are. |
| `benchmark` | Reruns the TTFT measurement on the current prompt, optionally against the SDK's default client. Changes no code. |
| `diagnose` | Reads the project and lists what slows the first token (prompt prefix that changes per turn, HTTP/1.1, no warm-up, thinking on, missing tools), ranked, with fixes. Needs no key or network. |

In Claude Code they are also commands: `/hopper-inference:integrate`, `/hopper-inference:benchmark`, `/hopper-inference:diagnose`.

## Connector

The plugin connects the Hopper MCP server at `https://withhopper.com/mcp`:

| Tool | Sign-in | What it does |
| :--- | :--- | :--- |
| `list_models` | No | Models, context length, prices |
| `get_integration_guide` | No | The tested integration code for LiveKit Agents, Pipecat, Vapi or the OpenAI SDK |
| `review_voice_agent_config` | No | Checks a system prompt, tools and client code for latency problems |
| `get_account` | Yes | Credits, spend and API keys (masked) |
| `create_api_key` | Yes | Creates an API key on your account and shows it once |

Sign-in uses your Hopper account (OAuth). The public tools work without it.

## Install

Claude Code:

```bash
claude plugin marketplace add hopper-inc/plugins
claude plugin install hopper-inference@hopper
```

Codex:

```bash
codex plugin marketplace add hopper-inc/plugins
codex plugin add hopper-inference@hopper
```

Then, in a voice-agent project: "Set up Hopper in this project and benchmark my agent's time to first token."

## What it runs, sends and stores

Everything it runs is readable Python in the skills' `scripts/` folders: standard library only, plus the `openai` and `h2` packages for the benchmark.

- **`hopper_trial.py`** registers an anonymous agent identity at `https://withhopper.com/agent/identity` ([protocol](https://withhopper.com/auth.md)) and exchanges it at `https://withhopper.com/oauth2/token` for a trial key. It writes the key to `.env` in the project as `HOPPER_API_KEY` without printing it, and saves the registration's claim token to `$TMPDIR/hopper-registration.json` (mode 600).
- **`hopper_ttft.py`** reads `HOPPER_API_KEY` and sends the agent's system prompt, its tool definitions and ten scripted caller turns to `https://api.withhopper.com/v1/chat/completions`. It prints timings and cache statistics. About $0.01–0.02 of credit per run.
- **`hopper_claim.py`**, only if you choose to keep the key, sends your email address and the saved claim token to `https://withhopper.com/agent/identity/claim` and `https://withhopper.com/oauth2/token`. After you enter the 6-digit code in your browser it writes the account key to `.env` and deletes the saved registration.
- **The `integrate` skill** runs `pip install openai h2` in the project's virtualenv, and after your go edits the file that builds the LLM client.
- **The connector** receives the arguments of the tool you call, and nothing else.

Requests to Hopper are handled under the [privacy policy](https://withhopper.com/privacy). Nothing else leaves your machine, and the plugin has no telemetry.

## Support

founders@withhopper.com · [Talk to us](https://withhopper.com/talk-to-us) · [Terms](https://withhopper.com/terms) · [Privacy](https://withhopper.com/privacy)

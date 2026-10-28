# Changelog

Versions follow the `version` in each plugin's manifest; `tools/check.mjs` keeps the manifests and `server.json` in step.

## Claude directory copy (hopper 1.3.0)

- `claude-directory/hopper`: the plugin as submitted to Claude's plugin directory, generated from `hopper/` by `tools/directory.mjs` (checked by `tools/check.mjs`). Anthropic's Software Directory Policy doesn't list software that generates audio, so it has no `hopper-speak` skill, no speak or voices commands in the transcribe script, and its connector is `https://withhopper.com/mcp/claude` (the MCP server without `speak` and `list_voices`). `hopper/` and the self-hosted marketplace are unchanged.

## hopper 1.3.0

- Positioning: a realtime inference API for open-source models in your agent (DeepSeek V4.1 Flash, Gemma 4 31B, Qwen 3 TTS, Nemotron ASR); no voice-agent branding in the listing, manifests or skills.
- Connector auth: `mcp.json` declares `extensions["com.openai"].auth` (`mixed`, CIMD client, scopes `account:read keys:write audio`), so ChatGPT sends the user's token after sign-in instead of calling `/mcp` anonymously. `.mcp.json` (Claude Code) is unchanged.
- New skill `hopper-try`: runs the user's own prompts (found in the project, or pasted) on DeepSeek V4.1 Flash and Gemma 4 31B side by side with time to first token, tokens per second and cost, a verdict per example, then offers a key or a switch. Uses the connector's `generate` tool where present and `scripts/hopper_try.py` (stdlib, streaming, optional `--tools`) where a shell has network. It is the new onboarding skill, with a first run that reaches a live answer in under a minute.
- `hopper-integrate`: from voice agents to any OpenAI-compatible project (OpenAI SDK Python/JS, LangChain, Vercel AI SDK, LiteLLM, raw HTTP, LiveKit, Pipecat, Vapi), with DeepSeek's thinking switch; key via `hopper_trial.py` or the connector's `create_api_key`. Voice agents keep the time-to-first-token run. Still edits only after the user says go.
- Removed `hopper-diagnose` and `hopper-benchmark` (benchmarking folds into `hopper-try`), their eval cases and unused fixtures; `tools/sync.mjs` no longer copies files into them.
- `hopper-speak` / `hopper-transcribe`: name Qwen 3 TTS / Nemotron ASR, and use the connector's `speak` / `transcribe` in ChatGPT, whose sandbox can't reach Hopper's API.
- Listing: new description, short description, long description, keywords, default prompts and review test cases (generate ×2, create_api_key, speak, transcribe; negatives: delete keys, Ollama, flight booking). `review_voice_agent_config` is gone from the connector and the listing.
- Evals: `triggers.json` rewritten for the new lineup (35 prompts); new `try-own-prompts` live case.

## hopper 1.2.3

- Review: demo recording URL for the OpenAI submission.

## hopper 1.2.2

- Listing: the long description names no other AI products or platforms (OpenAI's automated check).

## hopper 1.2.1

- Listing: the long description says what works in ChatGPT (inline audio player, transcribing attached recordings, models, integration code, latency review, account and keys) and scopes the project setup and 10-turn benchmark to Codex.
- Review test cases: speak (audio player) and transcribe (attached file) replace list_models and create_api_key among the five positives.

## hopper 1.2.0

- hopper-speak / hopper-transcribe: the agent's own trial key is checked for a writable ~/.config/hopper before it's created (Codex's sandbox used to lose it); sandbox blocks give `HOPPER_SANDBOX_BLOCKED` and exit 3 instead of a traceback.
- Handover: the scripts track the gateway's remaining-credit header and a local usage tally; under $0.50 they print `HOPPER_HANDOVER low_credit`, at zero `out_of_credit` (exit 4). The skills tell the agent to offer the user, once, to keep the key on their account (claim link + code on withhopper.com).
- Codex: escalation wording with a stated reason and a suggested allow rule, in every skill that calls the network; `agents/openai.yaml` per skill; the `.codex-plugin` overlay passes OpenAI's workspace validator.
- OpenAI build (tools/package.mjs): no Claude-only `allowed-tools`, no credit-purchase lines, no evals.

## hopper 1.1.0

- Connector: the Hopper MCP server at `https://withhopper.com/mcp` (speak, transcribe, list_voices, list_models, get_integration_guide, review_voice_agent_config without sign-in; get_account and create_api_key with Hopper sign-in).

## hopper 1.0.0 · hopper-announce 1.0.0 — unreleased

### hopper
- Skills: `hopper-integrate`, `hopper-benchmark`, `hopper-diagnose`, `hopper-speak`, `hopper-transcribe`.
- The Hopper MCP connector is held for the next version, until `https://withhopper.com/mcp` is live.
- Manifests for Claude Code, Codex and ChatGPT (portable `plugin.json` and `.codex-plugin/`), Cursor, and the MCP Registry.

### hopper-announce
- Speaks the first sentence of Claude Code's reply when a task took 20 seconds or more; adjustable with the `hopper-announce` skill.

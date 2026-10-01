# Changelog

Versions follow the `version` in each plugin's manifest; `tools/check.mjs` keeps the manifests and `server.json` in step.

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

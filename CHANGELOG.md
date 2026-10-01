# Changelog

Versions follow the `version` in each plugin's manifest; `tools/check.mjs` keeps the manifests and `server.json` in step.

## hopper 1.1.0

- Connector: the Hopper MCP server at `https://withhopper.com/mcp` (speak, transcribe, list_voices, list_models, get_integration_guide, review_voice_agent_config without sign-in; get_account and create_api_key with Hopper sign-in).

## hopper 1.0.0 · hopper-announce 1.0.0 — unreleased

### hopper
- Skills: `hopper-integrate`, `hopper-benchmark`, `hopper-diagnose`, `hopper-speak`, `hopper-transcribe`.
- The Hopper MCP connector is held for the next version, until `https://withhopper.com/mcp` is live.
- Manifests for Claude Code, Codex and ChatGPT (portable `plugin.json` and `.codex-plugin/`), Cursor, and the MCP Registry.

### hopper-announce
- Speaks the first sentence of Claude Code's reply when a task took 20 seconds or more; adjustable with the `hopper-announce` skill.

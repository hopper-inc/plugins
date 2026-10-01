# Hopper

The fastest LLM for voice agents, and a voice and ears for any agent. Hopper serves `gemma-4-31b` behind an OpenAI-compatible API with time to first token under 100 ms on a warm connection, plus text-to-speech and speech-to-text. An agent can start using it on its own: the first run registers a trial key ($2 credit) with no sign-up. Works in Claude Code, Codex, ChatGPT, Claude and Cursor, and anywhere Agent Skills run.

## Skills

| Skill | Say something like | What it does |
| :--- | :--- | :--- |
| `hopper-integrate` | "Make my voice agent respond faster" | Gets a trial key, benchmarks a 10-turn simulated call on the agent's own prompt and tools, shows the results, and after you say go switches only the LLM in LiveKit Agents, Pipecat, Vapi or OpenAI SDK code. STT, TTS and tools stay as they are. |
| `hopper-benchmark` | "How fast would my agent be on Hopper?" | Measures time to first token and prompt caching on the current prompt. Changes no code. |
| `hopper-diagnose` | "Why does my agent pause before answering?" | Reads the project and ranks what slows the first token, with fixes. Any provider; needs no key or network. |
| `hopper-speak` | "Read this aloud", "make an audio file of…" | Turns text into speech: plays it or saves a WAV, in any of 50 voices. |
| `hopper-transcribe` | "What does this recording say?" | Transcribes audio or video files (WAV, MP3, M4A, voice memos, MP4) with word timestamps. |

In Claude Code they are also commands, such as `/hopper:hopper-integrate`.

## Connector

The plugin connects the Hopper MCP server at `https://withhopper.com/mcp`, for hosts without a shell such as ChatGPT and Claude:

| Tool | Sign-in | What it does |
| :--- | :--- | :--- |
| `speak` | No | Text to speech, returned as audio and a short-lived link |
| `transcribe` | No | Speech to text from a WAV URL or upload, with word timestamps |
| `list_voices` | No | The ready voices |
| `list_models` | No | Models, context length, prices |
| `get_integration_guide` | No | The tested integration code for LiveKit Agents, Pipecat, Vapi or the OpenAI SDK |
| `review_voice_agent_config` | No | Checks a system prompt, tools and client code for latency problems |
| `get_account` | Yes | Credits, spend and API keys (masked) |
| `create_api_key` | Yes | Creates an API key on your account and shows it once |

Without sign-in, speech and transcription run on a small free daily allowance; signing in with your Hopper account (OAuth) bills your own credits.

## Install

```bash
claude plugin marketplace add https://withhopper.com/marketplace.json && claude plugin install hopper@hopper   # Claude Code
codex plugin marketplace add hopper-inc/plugins && codex plugin add hopper@hopper          # Codex
```

Pick one way to install: the plugin, or `npx skills add hopper-inc/plugins` for the skills alone. With both, every skill loads twice.

## What it runs, sends and stores

Everything it runs is readable Python in the skills' `scripts/` folders: standard library only, plus the `openai` and `h2` packages for the benchmark and `ffmpeg` to decode compressed audio.

- **`hopper_trial.py`** (integrate, benchmark) registers an anonymous agent identity at `https://withhopper.com/agent/identity` ([protocol](https://withhopper.com/auth.md)) and exchanges it at `https://withhopper.com/oauth2/token` for a trial key. It writes the key to the project's `.env` as `HOPPER_API_KEY` without printing it, and saves the claim token to `$TMPDIR/hopper-registration.json` (mode 600).
- **`hopper_ttft.py`** reads `HOPPER_API_KEY` and sends the agent's system prompt, its tool definitions and ten scripted caller turns to `https://api.withhopper.com/v1/chat/completions`. About $0.01–0.02 of credit per run.
- **`hopper_claim.py`**, only if you choose to keep the key, sends your email address and the saved claim token to `https://withhopper.com/agent/identity/claim` and `https://withhopper.com/oauth2/token`, then writes the account key to `.env`.
- **`hopper_voice.py`** (speak, transcribe) sends the text to speak to `https://api.withhopper.com/v1/audio/speech`, or the audio to transcribe to `https://api.withhopper.com/v1/audio/transcriptions`. It uses `HOPPER_API_KEY` or the project's `.env` if present; otherwise it registers a trial key the same way and keeps it in `~/.config/hopper/` (mode 600), never in the project. Its `claim` command moves that key to your account.
- **The connector** receives the arguments of the tool you call, and nothing else.
- **`hopper-integrate`** runs `pip install openai h2` in the project's virtualenv, and after your go edits the file that builds the LLM client.

Requests to Hopper are handled under the [privacy policy](https://withhopper.com/privacy). Nothing else leaves your machine, and the plugin has no telemetry.

## Support

founders@withhopper.com · [Talk to us](https://withhopper.com/talk-to-us) · [Terms](https://withhopper.com/terms) · [Privacy](https://withhopper.com/privacy)

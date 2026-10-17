# Hopper

Realtime inference API for open-source models in your agent: DeepSeek V4.1 Flash (`deepseek-v4.1-flash`) and Gemma 4 31B (`gemma-4-31b`) for text, Qwen 3 TTS for speech and Nemotron ASR for transcription, behind an OpenAI-compatible API at `https://api.withhopper.com/v1`. Test the models on your own prompts, then put a key in your code. An agent can start using Hopper on its own: the first run registers a key for it with no human step, and the user can later move that key to their Hopper account. Works in Claude Code, Codex, ChatGPT, Claude and Cursor, and anywhere Agent Skills run.

## Skills

| Skill | Say something like | What it does |
| :--- | :--- | :--- |
| `hopper-try` | "DeepSeek V4.1 Flash any good? Try it on my prompts" | Finds the prompts your app sends (or asks for a few examples), runs them on DeepSeek V4.1 Flash and Gemma 4 31B side by side with time to first token, tokens per second and cost, and gives a verdict per example. Changes no code. The onboarding skill. |
| `hopper-integrate` | "Switch this app to DeepSeek on Hopper" | Gets the project a key, shows the planned change, and after you say go points the project's OpenAI-compatible client at a Hopper model: OpenAI SDK (Python or JavaScript), LangChain, Vercel AI SDK, LiteLLM, raw HTTP, LiveKit Agents, Pipecat or Vapi. Voice agents also get a time-to-first-token run on their own prompt. |
| `hopper-speak` | "Read this aloud", "make an audio file of…" | Text to speech with Qwen 3 TTS: plays it or saves a WAV, in any of 50 voices. |
| `hopper-transcribe` | "What does this recording say?" | Speech to text with Nemotron ASR, for audio or video files (WAV, MP3, M4A, voice memos, MP4), with word timestamps. |

In Claude Code they are also commands, such as `/hopper:hopper-try`. Where a host has the connector (ChatGPT), the skills use its tools; scripts run only where the shell can reach Hopper's API (Codex CLI, Claude Code).

## Connector

The plugin connects the Hopper MCP server at `https://withhopper.com/mcp`. In ChatGPT it declares mixed sign-in (public tools plus Hopper OAuth), so after you connect your account, requests carry your token:

| Tool | Sign-in | What it does |
| :--- | :--- | :--- |
| `generate` | No | Runs a prompt or conversation on DeepSeek V4.1 Flash and/or Gemma 4 31B, side by side, with time to first token, tokens per second, tokens and cost |
| `list_models` | No | Models, context length, prices |
| `get_integration_guide` | No | Tested client code for the OpenAI SDK, LiveKit Agents, Pipecat or Vapi |
| `speak` | No | Text to speech (Qwen 3 TTS), returned as an audio player and a short-lived link |
| `transcribe` | No | Speech to text (Nemotron ASR) from an attached file, URL or upload, with word timestamps |
| `list_voices` | No | The ready voices |
| `get_account` | Yes | Credits, spend and API keys (masked) |
| `create_api_key` | Yes | Creates an API key on your account and returns a one-time link to copy it in the console, plus a ready snippet; the key never appears in the chat |

Without sign-in, model runs, speech and transcription have per-call and daily limits per caller; signed in with your Hopper account (OAuth), they use your own credits.

## Install

```bash
claude plugin marketplace add https://withhopper.com/marketplace.json && claude plugin install hopper@hopper   # Claude Code
codex plugin marketplace add hopper-inc/plugins && codex plugin add hopper@hopper          # Codex
```

Pick one way to install: the plugin, or `npx skills add hopper-inc/plugins` for the skills alone. With both, every skill loads twice.

## What it runs, sends and stores

Everything it runs is readable Python in the skills' `scripts/` folders: standard library only, plus the `openai` and `h2` packages for the voice-agent benchmark and `ffmpeg` to decode compressed audio.

- **`hopper_try.py`** (try) sends the prompts, system prompt and tool definitions you test to `https://api.withhopper.com/v1/chat/completions`, once per model, streamed. It uses `HOPPER_API_KEY` or the project's `.env` if present; otherwise it registers a trial key like `hopper_voice.py` does and keeps it in `~/.config/hopper/` (mode 600), never in the project. It changes no files in the project.
- **`hopper_trial.py`** (integrate) registers an anonymous agent identity at `https://withhopper.com/agent/identity` ([protocol](https://withhopper.com/auth.md)) and exchanges it at `https://withhopper.com/oauth2/token` for a trial key. It writes the key to the project's `.env` as `HOPPER_API_KEY` without printing it, and saves the claim token to `$TMPDIR/hopper-registration.json` (mode 600).
- **`hopper_ttft.py`** (integrate, voice agents) reads `HOPPER_API_KEY` and sends the agent's system prompt, its tool definitions and ten scripted caller turns to `https://api.withhopper.com/v1/chat/completions`. About $0.01–0.02 of credit per run.
- **`hopper_claim.py`**, only if you choose to keep the key, sends your email address and the saved claim token to `https://withhopper.com/agent/identity/claim` and `https://withhopper.com/oauth2/token`, then writes the account key to `.env`.
- **`hopper_voice.py`** (speak, transcribe) sends the text to speak to `https://api.withhopper.com/v1/audio/speech`, or the audio to transcribe to `https://api.withhopper.com/v1/audio/transcriptions`. It uses `HOPPER_API_KEY` or the project's `.env` if present; otherwise it registers a trial key the same way and keeps it in `~/.config/hopper/` (mode 600), never in the project. Its `claim` command moves that key to your account.
- **The connector** receives the arguments of the tool you call, and nothing else.
- **`hopper-integrate`** runs `pip install openai h2` in the project's virtualenv for a voice-agent benchmark, and after your go edits the file that builds the LLM client.

Requests to Hopper are handled under the [privacy policy](https://withhopper.com/privacy). Nothing else leaves your machine, and the plugin has no telemetry.

## Support

founders@withhopper.com · [Talk to us](https://withhopper.com/talk-to-us) · [Terms](https://withhopper.com/terms) · [Privacy](https://withhopper.com/privacy)

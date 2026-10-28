# Hopper

Realtime inference API for open-source models in your agent: DeepSeek V4.1 Flash (`deepseek-v4.1-flash`) and Gemma 4 31B (`gemma-4-31b`) for text, and Nemotron ASR (`nemotron-asr`) for transcription, behind an OpenAI-compatible API at `https://api.withhopper.com/v1`. Test the models on your own prompts, then put a key in your code.

## Skills

| Skill | Ask | What it does |
| --- | --- | --- |
| `hopper-try` | "Try the new DeepSeek on this prompt" | Runs your prompts, system prompt and tool definitions on Hopper's LLMs side by side, with time to first token, tokens per second and cost. Changes no files. |
| `hopper-integrate` | "Switch this app to DeepSeek on Hopper" | Gets the project a key, shows the planned change, and after you say go points the project's OpenAI-compatible client at a Hopper model: OpenAI SDK (Python or JavaScript), LangChain, Vercel AI SDK, LiteLLM, raw HTTP, LiveKit Agents, Pipecat or Vapi. Voice agents also get a time-to-first-token run on their own prompt. |
| `hopper-transcribe` | "What does this recording say?" | Speech to text with Nemotron ASR for audio or video files (WAV, MP3, M4A, voice memos, MP4), with word timestamps. |

## Connector

The plugin connects Claude to Hopper's MCP server at `https://withhopper.com/mcp/claude`.

| Tool | Sign-in | What it does |
| --- | --- | --- |
| `generate` | No | Runs a prompt on one or more of Hopper's LLMs, with time to first token, tokens per second and cost |
| `transcribe` | No | Speech to text with word timestamps, from an audio URL or base64 audio |
| `list_models` | No | Models, context lengths and prices |
| `get_integration_guide` | No | Client code for the OpenAI SDK, LiveKit Agents, Pipecat or Vapi |
| `get_account` | Yes | Credits, usage and API key names (never key secrets) |
| `create_api_key` | Yes | Creates a key; the secret opens once in the Hopper console |

`generate` and `transcribe` work without an account within daily limits. Signing in uses OAuth with your Hopper account, and usage is then billed to it.

## What it runs and sends

Everything the skills run is readable Python in their `scripts/` folders: standard library only, plus the `openai` and `h2` packages for the voice-agent benchmark and `ffmpeg` to decode compressed audio.

- **`hopper_try.py`** (try) sends the prompts, system prompt and tool definitions you test to `https://api.withhopper.com/v1/chat/completions`, once per model, streamed. It uses `HOPPER_API_KEY` or the project's `.env` if present; otherwise it registers a trial key through Hopper's agent registration (`https://withhopper.com/auth.md`) and keeps it in `~/.config/hopper/` (mode 600), never in the project. It changes no files in the project.
- **`hopper_trial.py`**, **`hopper_claim.py`** (integrate) register a trial key for the project the same way, and move it to your Hopper account when you ask.
- **`hopper_ttft.py`** (integrate, voice agents) reads `HOPPER_API_KEY` and sends the agent's system prompt, its tool definitions and ten scripted caller turns to `https://api.withhopper.com/v1/chat/completions`. About $0.01–0.02 of credit per run.
- **`hopper_voice.py`** (transcribe) sends the audio to transcribe to `https://api.withhopper.com/v1/audio/transcriptions`, with the same key lookup and trial registration as `hopper_try.py`. Its `claim` command moves the trial key to your account.
- **`hopper-integrate`** runs `pip install openai h2` in the project's virtualenv for a voice-agent benchmark, and after your go edits the file that builds the LLM client.

Keys are never printed. Text and audio you send go to Hopper's API. Privacy policy: https://withhopper.com/privacy. Terms: https://withhopper.com/terms. Support: founders@withhopper.com.

## License

MIT

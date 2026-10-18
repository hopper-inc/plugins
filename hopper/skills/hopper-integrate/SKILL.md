---
name: hopper-integrate
description: 'Points a project''s LLM calls at a Hopper model (DeepSeek V4.1 Flash or Gemma 4 31B) through Hopper''s OpenAI-compatible API: OpenAI SDK (Python or JavaScript), LangChain, Vercel AI SDK, LiteLLM, raw HTTP, LiveKit Agents, Pipecat or Vapi. Gets the project a key, shows the planned change (and, for a voice agent, time to first token on its own prompt), and edits code only after the user says go. Use when the user says "switch this app to DeepSeek on Hopper", "swap the LLM for Gemma 4", "move our OpenAI calls to Hopper", "point base_url at Hopper", "set up Hopper in this project", "add a Hopper API key to this repo" or "go ahead" after a hopper-try comparison. Not for trying or comparing models before deciding (hopper-try), speech or transcription (hopper-speak, hopper-transcribe), or running models locally.'
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_trial.py) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_claim.py *) Bash(python ${CLAUDE_SKILL_DIR}/scripts/hopper_ttft.py *) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_ttft.py *)
---

# Use a Hopper model in this project

Hopper serves DeepSeek V4.1 Flash (`deepseek-v4.1-flash`) and Gemma 4 31B (`gemma-4-31b`) behind an OpenAI-compatible API at `https://api.withhopper.com/v1`. Any code that talks to the OpenAI chat-completions API can use them by changing the base URL, the key and the model name.

Run this end to end. The user's only steps are reading the plan, opening one link to keep the key, and saying go before you change their code. Never ask them to sign up, copy keys by hand, or install anything Hopper-specific. Explicit instructions from the user override this workflow. If they haven't decided which model fits yet, or ask whether one is good enough, use the `hopper-try` skill in this plugin first.

Paths below start at `${CLAUDE_SKILL_DIR}`, the folder holding this file (if your host doesn't fill it in, use that folder's absolute path). Run the scripts from the project root: they read and write `.env` in the current directory. They need network access to `withhopper.com` and `api.withhopper.com`; in a sandbox (Codex), request escalated permissions for the first script, with the reason "Set up hopper: get this project a Hopper key (network to withhopper.com and api.withhopper.com; writes .env)", and suggest allowing commands that start with `python3` and the script's path. If the user declines, say Hopper couldn't run and ask how to continue.

## 1. Key

Skip this if `HOPPER_API_KEY` is already set, in the environment or in `.env`.

- **A shell with network** (Codex CLI, Claude Code):

  ```bash
  python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_trial.py
  ```

  Gets a trial key ($2 credit) through [agent registration](https://withhopper.com/auth.md), writes `HOPPER_API_KEY` to `.env` without printing it, and saves the registration privately for step 3. Check that `.env` is in `.gitignore`. Never print, commit, or ship the key to a browser.
- **No network from the shell** (ChatGPT's sandbox can't reach Hopper): call the Hopper connector's `create_api_key` tool (name it after the project, pass the chosen `model`). It returns a one-time link where the user copies the key, the `HOPPER_API_KEY=` line for `.env`, and a snippet. Never paste a full key into the chat. Skip step 3.

## 2. Find the LLM calls and plan

Locate every place the project builds an LLM client or calls a chat model: `OpenAI(`/`AsyncOpenAI(`, `new OpenAI(`, `ChatOpenAI(`, `createOpenAI(`/`@ai-sdk/openai`, `litellm.completion(`, `fetch(".../chat/completions")`, or a framework's LLM service. Note the current model, base URL and how the key is read. Pick the model the user chose (default `gemma-4-31b`; `deepseek-v4.1-flash` if they chose DeepSeek in hopper-try or asked for it).

**Voice agents only** (LiveKit Agents, Pipecat, Vapi, or any realtime conversational loop): measure time to first token on the agent's own system prompt and tools before proposing the change:

```bash
python3 -m pip install openai h2        # inside the project's virtualenv (python3 -m venv .venv if none)
set -a; . ./.env; set +a
python ${CLAUDE_SKILL_DIR}/scripts/hopper_ttft.py --prompt path/to/prompt.txt --tools tools.json --baseline
```

- `--prompt` is their system prompt; `--tools` is their tools in OpenAI format (`[{"type": "function", "function": {...}}]`), if any. With no project prompt, run it bare (a synthetic ~4k-token prompt). `--model` picks the model (default `gemma-4-31b`).
- A 10-turn simulated call on one warm HTTP/2 connection with the prompt warmed into the cache, then the same with `--baseline` (the SDK's defaults, no warm-up). About $0.02. `--cold` shows a never-seen prompt.
- Expect `protocol ['HTTP/2']` and a cache hit of 95% or more. Turns with no text mean the prompt calls tools you didn't pass. The random session ID the script puts at the top of the prompt is for measuring only; a real prompt must never do that.

## 3. Plan, and the link to keep the key

With a trial key from step 1, start the claim first so the link goes out with the plan. Confirm the user's email (`git config user.email` is a good guess) and run this in the background. It prints the link and code, then waits:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_claim.py user@example.com
```

Can't leave a command running? Add `--no-wait`; run it again later without the flag to resume waiting on the same code.

For a voice agent, send the report below as a fenced `text` block in exactly this layout (not a table), filled in from the script, with nothing before it and at most two one-line notes after it, only if a note changes the decision. Without a known city, drop "· measured from <city>":

```text
Hopper benchmark · <framework> agent · measured from <city>

                         SDK defaults    Tuned client
  First turn             <b1> ms         <h1> ms
  Later turns, median    <b2> ms         <h2> ms
  Prompt cache                           <hit>%

Keep this key: <link>  ·  code <code>  ·  expires in 10 minutes

Next: switch the LLM in <file> to Hopper (client and warm-up only; STT, TTS and tools unchanged). Go ahead?
```

Both columns are Hopper on their prompt and tools; their current provider isn't measured, so don't present either column as it.

For any other project, send:

```text
Hopper · <model>

  Change   <file>: base URL https://api.withhopper.com/v1, key HOPPER_API_KEY, model <model>
  Keeps    prompts, tools, streaming and the rest of the code as they are

Keep this key: <link>  ·  code <code>  ·  expires in 10 minutes

Next: make this change? Go ahead?
```

- Drop the "Keep this key" line when there's no claim link. The block always ends with "Go ahead?".
- When they enter the code, `hopper_claim.py` writes the account key to `.env` and exits 0. The trial key stops working then: restart any running process. Exit 2 means the code expired; run it again for a new one. If they don't keep it, the trial key works until its $2 runs out.

## 4. Connect (after a go)

Change only the LLM client: base URL, key, model, and the settings below. Keep prompts, tools and call sites as they are.

| Project uses | Do this |
| :--- | :--- |
| LiveKit Agents | `${CLAUDE_SKILL_DIR}/references/livekit.md` |
| Pipecat | `${CLAUDE_SKILL_DIR}/references/pipecat.md` |
| Vapi | `${CLAUDE_SKILL_DIR}/references/vapi.md` |
| OpenAI SDK, Python | `${CLAUDE_SKILL_DIR}/references/openai-sdk.md` (HTTP/2 client, one client per process) |
| OpenAI SDK, JavaScript/TypeScript | `new OpenAI({ apiKey: process.env.HOPPER_API_KEY, baseURL: "https://api.withhopper.com/v1" })`, created once and reused |
| LangChain | `ChatOpenAI(model=..., base_url="https://api.withhopper.com/v1", api_key=os.environ["HOPPER_API_KEY"])` (JS: `configuration: { baseURL }`) |
| Vercel AI SDK | `const hopper = createOpenAI({ baseURL: "https://api.withhopper.com/v1", apiKey: process.env.HOPPER_API_KEY })`, then `hopper.chat("<model>")` |
| LiteLLM | `model="openai/<model>"`, `api_base="https://api.withhopper.com/v1"`, `api_key=os.environ["HOPPER_API_KEY"]` |
| Raw HTTP | `POST https://api.withhopper.com/v1/chat/completions` with `Authorization: Bearer $HOPPER_API_KEY` and an OpenAI chat-completions body |

The reference pages are tested against the live API with `gemma-4-31b`; for DeepSeek, change the model name and add the thinking switch below. In voice agents, start the warm-up in the background as the pages do (`asyncio.create_task`); awaiting it delays every call. Read the key from the environment (`HOPPER_API_KEY`), never hard-code it, and add it to `.env.example` or the deploy config's secret list without a value.

Then run the project's own tests or one real request through the changed code path, and report the result in one or two lines.

## Model settings

| Model | Setting |
| :--- | :--- |
| `deepseek-v4.1-flash` | Thinks before answering unless told not to. For direct answers send `chat_template_kwargs: {"thinking": false}` (Python SDK: `extra_body={"chat_template_kwargs": {"thinking": False}}`; JS: pass it in the request body). |
| `gemma-4-31b` | No `reasoning_effort`: any value, even `low`, turns thinking on and adds seconds. |

## Keeping latency low

| Rule | Why |
| :--- | :--- |
| **One client per process**, reused, on HTTP/2 with a long keepalive (Python: `h2` installed and `http2=True`, as the references do). | A new client per request pays a TLS handshake each time. |
| **Identical prefix.** System prompt and tools byte-identical across requests, tools in the same order; per-request data goes at the end. Append history; never rewrite earlier turns. | Hopper's prompt cache matches from the first token. |
| **Stream** where the app shows or speaks text as it arrives, with `stream_options.include_usage`. | First tokens reach the user sooner, and `cached_tokens` shows up in usage. |

## Fails silently

- **HTTP/1.1** in Python means `h2` is missing. The SDK falls back without an error.
- **A timestamp or request ID at the top** of the prompt drops the cache hit to near zero.
- **Tools named in the prompt but not sent** give empty replies on the turns that try to call them.
- **DeepSeek with thinking on** can spend the whole `max_tokens` budget before any answer text.
- **After a claim**, the trial key returns 401. Update everything that holds it (`.env`, Vapi's Custom LLM key, deploy secrets).
- **openai 3.x uses `httpx2`, not `httpx`.** Build Python clients through `openai.DefaultAsyncHttpxClient`, as the references do.

## Reference

| | |
| :--- | :--- |
| Base URL | `https://api.withhopper.com/v1` |
| Models | `deepseek-v4.1-flash` · `gemma-4-31b` (262,144-token context) |
| Prices and context | the connector's `list_models` tool, or https://withhopper.com/console |
| Limits | 2,000 requests/min per key (429 with `Retry-After`) · zero balance returns 402 `insufficient_quota` |
| Keys | https://withhopper.com/console/keys |
| Agent registration | https://withhopper.com/auth.md |
| Errors | https://docs.withhopper.com/errors |

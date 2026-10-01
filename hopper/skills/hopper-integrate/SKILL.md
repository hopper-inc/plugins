---
name: hopper-integrate
description: 'Switch an existing voice agent''s LLM to Hopper, an OpenAI-compatible endpoint built for low time to first token. Gets a key for the project with no human step, benchmarks the agent''s own prompt and tools, and edits code only after the user says go. Use when the user says "make my agent respond faster", "set up Hopper", "try Hopper" or "swap the LLM" in a Pipecat, LiveKit Agents, Vapi or OpenAI-SDK voice agent. For numbers only, use hopper-benchmark; to find what''s slow, use hopper-diagnose.'
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_trial.py) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_claim.py *) Bash(python ${CLAUDE_SKILL_DIR}/scripts/hopper_ttft.py *) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_ttft.py *)
---

# Hopper for voice agents

Hopper serves `gemma-4-31b` behind an OpenAI-compatible API at `https://api.withhopper.com/v1`. Every voice-agent turn resends the same long prompt; Hopper caches it, so with a warm connection every turn, the first included, starts in well under 100 ms.

Run this end to end. The user's only steps are reading the results, opening one link to keep the key, and saying go before you change their code. Never ask them to sign up, copy keys, or install anything Hopper-specific. Explicit instructions from the user override this workflow.

Paths below start at `${CLAUDE_SKILL_DIR}`, the folder holding this file (if your host doesn't fill it in, use that folder's absolute path). Run the scripts from the project root: they read and write `.env` in the current directory. They need network access to `withhopper.com` and `api.withhopper.com`; if the sandbox blocks it, ask for approval to run with network access.

## 1. Trial key

Skip this if `HOPPER_API_KEY` is already set, in the environment or in `.env`.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_trial.py
```

- Gets a trial key ($2 credit) through [agent registration](https://withhopper.com/auth.md) and writes `HOPPER_API_KEY` to `.env` without printing it.
- Saves the registration privately for step 3.
- Check that `.env` is in `.gitignore`. Never print, commit, or ship the key to a browser.

## 2. Benchmark

```bash
python3 -m pip install openai h2        # inside the project's virtualenv (python3 -m venv .venv if none)
set -a; . ./.env; set +a
python ${CLAUDE_SKILL_DIR}/scripts/hopper_ttft.py --prompt path/to/prompt.txt --tools tools.json --baseline
```

- **Use the user's own agent.** `--prompt` is their system prompt. `--tools` is their tools in OpenAI format (`[{"type": "function", "function": {...}}]`), if they have any. With no project prompt, run it bare: a synthetic ~4k-token prompt.
- **What it does:** a 10-turn call on one warm HTTP/2 connection, with the prompt warmed into the cache first and 6 s between turns, then the same call with `--baseline` (the SDK's defaults, no warm-up) for the before column. About $0.02.
- **Option:** `--cold` shows a never-seen prompt.
- **Expect** `protocol ['HTTP/2']` and a cache hit of 95% or more on every turn. Turns with no text mean the prompt calls tools you didn't pass.
- **Reference**, from Santa Clara on a home ISP, 1.9k-token prompt with tools: turn 1 60 ms, later turns 63 ms median. `--baseline`: 170 ms, then 134 ms.
- The random session ID the script puts at the top of the prompt is for measuring only; a real prompt must never do that.

## 3. Results, and the link to keep the key

Start the claim first, so the link goes out with the numbers. Confirm the user's email (`git config user.email` is a good guess) and run this in the background. It prints the link and code, then waits:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_claim.py user@example.com
```

Can't leave a command running? Add `--no-wait`. It prints the link and code and exits; run it again later without the flag to resume waiting on the same code.

Then send the report below as a fenced `text` block, in exactly this layout (not a table): filled in, nothing before it, nothing after it except up to two one-line notes, and only if a note changes the decision (for example, "Your agent already points at Hopper; only the client tuning is missing"). No method explanations, footnotes, or remarks about this skill. Without a known city, drop "· measured from <city>".

```text
Hopper benchmark · <framework> agent · measured from <city>

                         SDK defaults    Tuned client
  First turn             <b1> ms         <h1> ms
  Later turns, median    <b2> ms         <h2> ms
  Prompt cache                           <hit>%

Keep this key: <link>  ·  code <code>  ·  expires in 10 minutes

Next: switch the LLM in <file> to Hopper (client and warm-up only; STT, TTS and tools unchanged). Go ahead?
```

- Keep this format even without a claim link: then drop only the "Keep this key" line. The block always ends with the "Next: … Go ahead?" line.
- Both columns are Hopper on their prompt and tools. **Tuned client** is the run the pages set up (warm HTTP/2 connection, prompt warmed into the cache); **SDK defaults** is the same run with `--baseline`. Their current provider isn't measured; don't present either column as it.
- When they enter the code, `hopper_claim.py` writes the account key to `.env` and exits 0. The trial key stops working then: restart any running agent process.
- Exit 2 means the code expired; run it again for a new one. If they don't keep it, the trial key works until its $2 runs out.

## 4. Connect (after a go)

Change only the LLM. Each page is tested against the live API with a tool-calling agent; copy its code as is. Start the warm-up in the background as the page does (`asyncio.create_task`); awaiting it delays the start of every call.

| Project uses | Page |
| :--- | :--- |
| LiveKit Agents | `${CLAUDE_SKILL_DIR}/references/livekit.md` |
| Pipecat | `${CLAUDE_SKILL_DIR}/references/pipecat.md` |
| Vapi | `${CLAUDE_SKILL_DIR}/references/vapi.md` |
| OpenAI SDK, or anything else | `${CLAUDE_SKILL_DIR}/references/openai-sdk.md` |

Then make a test call and compare the framework's TTFT metric with step 2.

## Keeping TTFT low

| Rule | Why |
| :--- | :--- |
| **Identical prefix.** System prompt and tools byte-identical across turns and calls, tools in the same order. Per-call data (name, date, call ID) goes at the end of the prompt. Append history; never rewrite earlier turns. | The cache matches from the first token. |
| **No cold starts.** One client per process on HTTP/2 with a long keepalive, plus a 1-token warm-up with the prompt and tools when a call starts or the prompt changes. | Turn 1 becomes a cache hit on a warm connection. Every reference does both. |
| **Stream every turn**, with `stream_options.include_usage`. | Text reaches TTS as it arrives, and `cached_tokens` shows up in the logs. |
| **No `reasoning_effort`.** | Any value, even `low`, turns thinking on for `gemma-4-31b` and adds seconds. |

## Fails silently

- **HTTP/1.1** in the benchmark output means `h2` is missing. The SDK falls back without an error.
- **A timestamp or call ID at the top** of the prompt drops the cache hit to near zero on every turn.
- **Tools named in the prompt but not sent** give empty replies on the turns that try to call them: dead air, no error.
- **After a claim**, the trial key returns 401. Update everything that holds it (`.env`, Vapi's Custom LLM key).
- **openai 3.x uses `httpx2`, not `httpx`.** Build clients through `openai.DefaultAsyncHttpxClient`, as the references do.

## Reference

| | |
| :--- | :--- |
| Base URL | `https://api.withhopper.com/v1` |
| Model | `gemma-4-31b` · 262,144-token context, output included |
| Price per 1M tokens | $0.40 input · $0.20 cached input · $1.20 output |
| Limits | 2,000 requests/min per key (429 with `Retry-After`) · zero balance returns 402 `insufficient_quota` |
| Credits | $2 trial · $5 once claimed · top up in the [console](https://withhopper.com/console) |
| Agent registration | https://withhopper.com/auth.md |
| Errors | https://docs.withhopper.com/errors |
| Speech to text · Text to speech | https://docs.withhopper.com/stt · https://docs.withhopper.com/tts |

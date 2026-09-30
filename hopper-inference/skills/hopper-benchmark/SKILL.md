---
name: hopper-benchmark
description: 'Measure a voice agent''s LLM time to first token on Hopper with its own system prompt and tools over a simulated 10-turn call, and report first-turn and later-turn latency and the prompt-cache hit rate. Changes no code. Use when the user asks "how fast would my agent be on Hopper", "benchmark TTFT", "is prompt caching working" or wants before/after numbers. Not for STT/TTS latency or load tests; to switch the agent to Hopper, use hopper-integrate.'
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_trial.py) Bash(python ${CLAUDE_SKILL_DIR}/scripts/hopper_ttft.py *) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_ttft.py *)
---

# Benchmark a voice agent on Hopper

Paths below start at `${CLAUDE_SKILL_DIR}`, the folder holding this file (if your host doesn't fill it in, use that folder's absolute path). Run from the project root. The scripts need network access to `withhopper.com` and `api.withhopper.com`; if the sandbox blocks it, ask for approval. This measures only; don't change project code. Explicit instructions from the user override these steps.

## 1. Key

Use `HOPPER_API_KEY` from the environment or `.env`. If there is none, get a trial key ($2 credit, no sign-up; writes `.env` without printing the key), and check that `.env` is in `.gitignore`:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_trial.py
```

## 2. Inputs

Find the agent's system prompt and tools in the project. Write the prompt as the agent sends it to a temp file, and the tools in OpenAI format (`[{"type": "function", "function": {...}}]`) to another. Extract them from source without running the agent. With no prompt in the project, run without `--prompt`: a synthetic ~4k-token prompt.

## 3. Run

```bash
python3 -m pip install openai h2        # inside the project's virtualenv
set -a; . ./.env; set +a
python ${CLAUDE_SKILL_DIR}/scripts/hopper_ttft.py --prompt "$PROMPT_FILE" --tools "$TOOLS_FILE"
```

| Flag | Use it when |
| :--- | :--- |
| `--baseline` | The user wants a before column: the same call with the SDK's default client and no warm-up |
| `--cold` | The user asks about a never-seen prompt (first call after a deploy or a prompt change) |
| `--gap <s>` | The agent's turns are spaced differently from the default 6 s |

A run is 10 turns, about $0.01 (twice that with `--baseline`).

## 4. Report

Send this as a fenced `text` block in exactly this layout (not a table), filled in from the script's output, and nothing else except at most two one-line notes that change a decision. Without a known city, drop "· measured from <city>":

```text
Hopper benchmark · <framework> agent · measured from <city>

                         SDK defaults    Tuned client
  First turn             <b1> ms         <h1> ms
  Later turns, median    <b2> ms         <h2> ms
  Prompt cache                           <hit>%
```

Both columns are Hopper on the agent's prompt: **Tuned client** is the default run, **SDK defaults** the `--baseline` run. Drop the SDK defaults column without `--baseline`. If an earlier run's numbers are in the conversation, put them in that column instead and name it after that run. The project's current provider isn't measured; don't label a column as it.

Read the output this way:
- `protocol ['HTTP/1.1']` means `h2` isn't installed in the environment that ran the script.
- A cache hit under 95% on later turns means the prompt's start changes between turns: look for a timestamp, call ID or random value near the top.
- Turns with no text mean the prompt calls tools that weren't passed with `--tools`.

To make these numbers hold in production, the `hopper-integrate` skill in this plugin switches the project's client; the `hopper-diagnose` skill finds what else slows it down.

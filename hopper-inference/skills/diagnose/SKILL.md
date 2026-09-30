---
name: diagnose
description: Find what makes a voice agent's LLM slow to start responding, by reading the project's code, prompt and tools, and list fixes ranked by the latency they recover. Use when the user reports slow responses, long pauses, dead air or high time to first token in a Pipecat, LiveKit Agents, Vapi or OpenAI-SDK voice agent, or asks for a latency review. Works whichever LLM provider the project uses.
---

# Diagnose voice-agent LLM latency

Read the project; don't change code until the user picks fixes. Explicit instructions from the user override these steps. No key or network is needed.

## 1. Find the LLM path

Locate where the agent builds its LLM client or service, where it assembles the system prompt, which tools it sends, and where a call starts. Note the framework (LiveKit Agents, Pipecat, Vapi, the OpenAI SDK directly, or other) and the provider (`base_url`, model).

## 2. Check each item

Check every row. For each hit, record the file and line.

| # | Look for | Why it's slow | Fix |
| :- | :--- | :--- | :--- |
| 1 | A timestamp, date, call ID, caller name, UUID or random value in the first part of the system prompt, or tools built per call in a varying order | The prompt cache matches from the first token, so every turn pays full prefill | Keep the prompt and tools byte-identical across turns and calls; move per-call values to the end of the prompt |
| 2 | Earlier turns rewritten, summarised or re-rendered each turn | Same: the prefix changes | Append history; never edit earlier messages |
| 3 | A new client or HTTP connection per request or per call (`OpenAI(...)` or `AsyncOpenAI(...)` inside the turn handler, `httpx` client in a `with` block per call) | A TLS handshake on the turn: typically 50–150 ms | One client per process, reused |
| 4 | The client on HTTP/1.1: no `http2=True`, or `h2` missing from the project's requirements | Head-of-line blocking and extra connections under concurrency | `openai.DefaultAsyncHttpxClient(http2=True, ...)` and `h2` in requirements. The SDK falls back to HTTP/1.1 silently without `h2` |
| 5 | Keepalive shorter than the gap between turns (httpx's default is 5 s) | The connection closes while the caller talks, so the next turn reconnects | `keepalive_expiry` of 300 s |
| 6 | No warm-up when a call starts | Turn 1 is a cold connection and a cache miss | Send a 1-token request with the real system prompt and tools as the call starts, through the same code path as a turn |
| 7 | `stream=False`, or text sent to TTS only after the whole reply | TTS waits for the full completion | Stream every turn and forward text as it arrives |
| 8 | `reasoning_effort`, thinking or reasoning enabled | The model thinks before the first spoken token: seconds | Remove it for conversational turns |
| 9 | Tools named or described in the prompt but not sent in `tools` | The model tries to call them and produces no speech: dead air | Send every tool the prompt mentions, or remove the mention |
| 10 | A connect timeout above a few seconds, or retries without a timeout | A stalled connection becomes a long silence | `connect=3.0`, with a bounded retry |
| 11 | Large dynamic context (RAG results, CRM records) inserted near the top of the prompt | Invalidates the cache from that point on | Put it at the end, after the static instructions |

For framework-specific code, read the matching page in this skill: `${CLAUDE_SKILL_DIR}/references/livekit.md`, `pipecat.md`, `vapi.md` or `openai-sdk.md` in the same folder. `${CLAUDE_SKILL_DIR}` is the folder holding this file (if your host doesn't fill it in, use that folder's absolute path). If the Hopper connector is available, its `review_voice_agent_config` tool runs the prompt and tools checks too.

## 3. Report

```text
Voice-agent latency review · <framework> · <provider/model>

  #  Finding                                   Where                 Recovers
  1  <finding>                                 <file:line>           <estimate>
  ...

Fix 1–<n> now? The rest need <what>.
```

- Rank by the latency recovered: per-turn issues (1, 2, 8, 9) before first-turn issues (3–6).
- Say "no issues found" for a clean project; don't pad the list.
- To measure instead of estimate, the `benchmark` skill in this plugin times the agent's own prompt on Hopper.

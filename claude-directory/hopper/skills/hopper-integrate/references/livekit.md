# Hopper LLM in LiveKit Agents

Use LiveKit's own OpenAI plugin (`livekit-plugins-openai`) pointed at Hopper. There is nothing Hopper-specific to install. Change only the LLM; keep STT, TTS, VAD and turn detection as they are.

Verified with livekit-agents 1.8 (which resolves openai 2.x): tool calls run and the model answers from their results, the first turn of a call is a prompt-cache hit, and TTFT is near 60 ms per turn (about 175 ms on a tool-call turn).

## Dependencies

```bash
pip install "livekit-agents[openai]" h2   # inside the project's virtualenv
```

Add `h2` to the project's requirements too. It enables HTTP/2 in the HTTP library the OpenAI SDK already uses; without it deploys fall back to HTTP/1.1 silently.

## Code

```python
import os

import openai
from livekit.agents import Agent, llm as lk_llm
from livekit.plugins import openai as lk_openai


def voice_http_client():
    """HTTP/2, a keepalive that outlives the gaps between turns, fast connect timeout."""
    Limits = type(openai.DEFAULT_CONNECTION_LIMITS)
    Timeout = type(openai.DEFAULT_TIMEOUT)
    return openai.DefaultAsyncHttpxClient(
        http2=True,
        limits=Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=300.0),
        timeout=Timeout(60.0, connect=3.0),
    )


def hopper_llm() -> lk_openai.LLM:
    return lk_openai.LLM(
        model="gemma-4-31b",
        client=openai.AsyncOpenAI(
            api_key=os.environ["HOPPER_API_KEY"],
            base_url="https://api.withhopper.com/v1",
            http_client=voice_http_client(),
        ),
    )


async def warm_up(llm: lk_openai.LLM, agent: Agent) -> None:
    """Put the agent's instructions and tools in Hopper's prompt cache.

    Sent through the same llm.chat() path the session uses, so the prefix is
    byte-identical to the real first turn.
    """
    ctx = lk_llm.ChatContext()
    ctx.add_message(role="system", content=agent.instructions)
    async with llm.chat(chat_ctx=ctx, tools=list(agent.tools), extra_kwargs={"max_completion_tokens": 1}) as stream:
        async for _ in stream:
            pass
```

## Wire it in

In the entrypoint, build the LLM and start the warm-up in the background as the session starts; it finishes (about 300 ms) long before the caller's first reply:

```python
llm = hopper_llm()
agent = MyAgent()  # the project's Agent subclass
warm = asyncio.create_task(warm_up(llm, agent))  # keep a reference until it finishes
session = AgentSession(llm=llm, stt=..., tts=..., vad=...)  # the project's existing STT/TTS/VAD
await session.start(agent, room=ctx.room)
```

Create one client per worker process if the project already caches plugins in `prewarm`; the connection is reused across calls either way.

## Rules

- Keep `instructions` and the tool list identical across turns and calls; put per-call data at the end of the instructions. The cache matches from the first token.
- Don't pass `reasoning_effort`: it turns thinking on for `gemma-4-31b` and adds seconds.
- Per-turn latency: `LLMMetrics.ttft` and `LLMMetrics.prompt_cached_tokens` (via `ChatMessage.metrics` or `session_usage_updated`). Cached tokens near the prompt size on every turn, the first included, means the warm-up and prefix are right.

# Hopper LLM with the OpenAI SDK

For agents built directly on the OpenAI Python SDK (1.x through 3.x). Replace the client construction; keep every call as it is. Streaming, `tools`, `tool_choice`, and `tool` messages work unchanged.

## Dependencies

```bash
pip install openai h2   # inside the project's virtualenv
```

Add `h2` to the project's requirements too. It enables HTTP/2 in the HTTP library the OpenAI SDK already uses; without it deploys fall back to HTTP/1.1 silently.

## Code

```python
import os

import openai


def voice_http_client():
    """HTTP/2, a keepalive that outlives the gaps between turns, fast connect timeout."""
    Limits = type(openai.DEFAULT_CONNECTION_LIMITS)
    Timeout = type(openai.DEFAULT_TIMEOUT)
    return openai.DefaultAsyncHttpxClient(
        http2=True,
        limits=Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=300.0),
        timeout=Timeout(60.0, connect=3.0),
    )


client = openai.AsyncOpenAI(
    api_key=os.environ["HOPPER_API_KEY"],
    base_url="https://api.withhopper.com/v1",
    http_client=voice_http_client(),
)


async def warm_up(system_prompt: str, tools=None) -> None:
    """Open the connection and put the system prompt (and tools) in Hopper's prompt cache."""
    extra = {"tools": tools} if tools else {}
    await client.chat.completions.create(
        model="gemma-4-31b",
        messages=[{"role": "system", "content": system_prompt}],
        max_tokens=1,
        **extra,
    )
```

Create `client` once per process and call `warm_up` at startup and whenever the prompt changes. Pass exactly the `tools` list the turns send, in the same order, so the cached prefix matches.

Each turn: send the whole history with `stream=True` and `stream_options={"include_usage": True}`, forward text to TTS as it arrives, and read `usage.prompt_tokens_details.cached_tokens` on the last chunk.

In other languages, point the OpenAI SDK at `https://api.withhopper.com/v1`, create one client per process, use HTTP/2 if the HTTP library supports it, set the keepalive to at least 300 s, and send the same 1-token warm-up.

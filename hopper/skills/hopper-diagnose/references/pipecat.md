# Hopper LLM in Pipecat

Use Pipecat's own `OpenAILLMService` pointed at Hopper, with a voice-tuned HTTP client. There is nothing Hopper-specific to install. Change only the LLM service; keep STT, TTS, VAD and transport as they are.

Verified with pipecat-ai 1.12 on openai 2.x and 3.x: registered functions run and the model answers from their results, the first turn of a call is a prompt-cache hit, and TTFT (Pipecat's TTFB metric) is near 60 ms per turn.

## Dependencies

```bash
pip install "pipecat-ai[openai]" h2   # inside the project's virtualenv
```

Add `h2` to the project's requirements too. It enables HTTP/2 in the HTTP library the OpenAI SDK already uses; without it deploys fall back to HTTP/1.1 silently.

## Code

```python
import os

import openai
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.services.openai.llm import OpenAILLMService


def voice_http_client():
    """HTTP/2, a keepalive that outlives the gaps between turns, fast connect timeout."""
    Limits = type(openai.DEFAULT_CONNECTION_LIMITS)
    Timeout = type(openai.DEFAULT_TIMEOUT)
    return openai.DefaultAsyncHttpxClient(
        http2=True,
        limits=Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=300.0),
        timeout=Timeout(60.0, connect=3.0),
    )


class HopperLLMService(OpenAILLMService):
    def create_client(self, api_key=None, base_url=None, organization=None, project=None, default_headers=None, **kwargs):
        return openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            organization=organization,
            project=project,
            default_headers=default_headers,
            http_client=voice_http_client(),
        )


def hopper_llm(system_prompt: str) -> HopperLLMService:
    return HopperLLMService(
        api_key=os.environ["HOPPER_API_KEY"],
        base_url="https://api.withhopper.com/v1",
        settings=OpenAILLMService.Settings(model="gemma-4-31b", system_instruction=system_prompt),
    )


async def warm_up(llm: HopperLLMService, tools) -> None:
    """Put the system prompt and tools in Hopper's prompt cache.

    run_inference builds its request exactly like a pipeline turn, so the
    prefix is byte-identical to the real first turn.
    """
    await llm.run_inference(LLMContext(tools=tools), max_tokens=1)
```

## Wire it in

Build the LLM where the project builds its current one, register functions as before, and start the warm-up in the background from the async code that starts the pipeline (it needs a running event loop). It finishes, in about 300 ms, long before the caller's first reply:

```python
llm = hopper_llm(SYSTEM_PROMPT)
llm.register_function("check_availability", check_availability)  # the project's existing handlers
context = LLMContext(tools=tools)  # the project's existing ToolsSchema
warm = asyncio.create_task(warm_up(llm, tools))  # keep a reference until it finishes
task = PipelineTask(pipeline, params=PipelineParams(enable_metrics=True, enable_usage_metrics=True))
```

Keep `llm` where the old LLM service sat in the pipeline, between the user context aggregator and TTS. The system prompt goes in `Settings.system_instruction`, not as a context message, so the warm-up and every turn share it.

## Rules

- Keep the system prompt and tools identical across turns and calls; put per-call data at the end of the system prompt. The cache matches from the first token.
- Don't pass `reasoning_effort` (for example through `Settings.extra`): it turns thinking on for `gemma-4-31b` and adds seconds.
- Per-turn latency: `TTFBMetricsData`, and `LLMUsageMetricsData.value.cache_read_input_tokens` for cache hits, with `PipelineParams(enable_metrics=True, enable_usage_metrics=True)`. Cached tokens near the prompt size on every turn, the first included, means the warm-up and prefix are right.

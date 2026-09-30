import asyncio
import os

import openai

PROMPT = open("prompt.txt").read()

TOOLS = [
    {"type": "function", "function": {
        "name": "lookup_order",
        "description": "Look up an order by its number.",
        "parameters": {"type": "object", "properties": {"order_number": {"type": "string"}}, "required": ["order_number"]},
    }},
    {"type": "function", "function": {
        "name": "transfer_call",
        "description": "Transfer the caller to a human agent.",
        "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]},
    }},
]

Limits = type(openai.DEFAULT_CONNECTION_LIMITS)
Timeout = type(openai.DEFAULT_TIMEOUT)
client = openai.AsyncOpenAI(
    api_key=os.environ["HOPPER_API_KEY"],
    base_url="https://api.withhopper.com/v1",
    http_client=openai.DefaultAsyncHttpxClient(
        http2=True,
        limits=Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=300.0),
        timeout=Timeout(60.0, connect=3.0),
    ),
)


def system_prompt(caller_name: str) -> str:
    return f"{PROMPT}\n\nCaller name: {caller_name}"


async def warm_up(caller_name: str) -> None:
    await client.chat.completions.create(
        model="gemma-4-31b",
        messages=[{"role": "system", "content": system_prompt(caller_name)}],
        tools=TOOLS,
        max_completion_tokens=1,
    )


_background = set()


def start_call(caller_name: str) -> None:
    """Called when a call connects: warms the connection and the prompt cache while the greeting plays."""
    task = asyncio.create_task(warm_up(caller_name))
    _background.add(task)
    task.add_done_callback(_background.discard)


async def respond(history: list[dict], caller_name: str):
    stream = await client.chat.completions.create(
        model="gemma-4-31b",
        messages=[{"role": "system", "content": system_prompt(caller_name)}, *history],
        tools=TOOLS,
        stream=True,
        stream_options={"include_usage": True},
    )
    async for chunk in stream:
        yield chunk

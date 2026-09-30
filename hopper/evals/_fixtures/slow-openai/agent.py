import os
import uuid
from datetime import datetime

from openai import AsyncOpenAI

BASE_PROMPT = open("prompt.txt").read()

TOOLS = [
    {"type": "function", "function": {
        "name": "lookup_order",
        "description": "Look up an order by its number.",
        "parameters": {"type": "object", "properties": {"order_number": {"type": "string"}}, "required": ["order_number"]},
    }},
]


def system_prompt(call_id: str) -> str:
    now = datetime.now().isoformat()
    return f"Current time: {now}\nCall ID: {call_id}\n\n{BASE_PROMPT}"


async def respond(history: list[dict], call_id: str) -> str:
    client = AsyncOpenAI(api_key=os.environ["LLM_API_KEY"], base_url=os.environ.get("LLM_BASE_URL"))
    response = await client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "gpt-5-mini"),
        messages=[{"role": "system", "content": system_prompt(call_id)}, *history],
        tools=TOOLS,
        reasoning_effort="low",
        stream=False,
    )
    return response.choices[0].message.content or ""


def new_call() -> str:
    return str(uuid.uuid4())

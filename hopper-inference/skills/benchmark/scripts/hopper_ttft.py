"""Hopper TTFT check for voice agents.

Replays a voice-agent conversation against Hopper: a ~4k-token system prompt
that stays identical across turns (so 95%+ of every request is a prefix-cache
hit), streaming on, and a pause between turns the way TTS playback and the
caller's reply create one. The client is the stock OpenAI SDK, tuned the way a
voice agent should run it: one warm HTTP/2 connection with a long keepalive,
opened before the first turn.

    pip install openai h2
    HOPPER_API_KEY=sk_hopper_... python hopper_ttft.py [--prompt system_prompt.txt] [--tools tools.json]
"""

import argparse
import asyncio
import json
import os
import statistics
import time
import uuid

import openai
from openai import AsyncOpenAI

CALLER_TURNS = [
    "Hi, I'm calling about my appointment next week.",
    "It's under Jordan Lee, the Tuesday one.",
    "Can we move it to Thursday afternoon instead?",
    "Anything after two works for me.",
    "Three thirty is perfect.",
    "Do I need to bring anything with me?",
    "Is there parking at the Oak Street location?",
    "Great. And can you text me a confirmation?",
    "Yes, this number is fine.",
    "No, that's everything. Thanks!",
]


def synthetic_system_prompt() -> str:
    """~4k tokens shaped like a production voice-agent prompt."""
    rules = "\n".join(
        f"- Rule {i}: when the caller asks about policy area {i}, answer in one "
        f"short sentence, confirm the detail back, and never read out internal "
        f"codes, markup, or tool names."
        for i in range(1, 51)
    )
    locations = "\n".join(
        f"- Location {i}: {100 + i} Oak Street, open 8am to 6pm weekdays, "
        f"9am to 1pm Saturday, closed Sunday, parking behind the building."
        for i in range(1, 46)
    )
    return (
        "# Identity\nYou are Riley, the phone assistant for Northside Clinics. "
        "You are speaking on a live phone call. Keep every reply under two "
        "sentences, plain spoken English, no lists or formatting.\n\n"
        f"# Rules\n{rules}\n\n# Locations\n{locations}\n"
    )


def voice_http_client(**extra):
    """The OpenAI SDK's own HTTP client, tuned for voice: HTTP/2 (one
    connection multiplexes every call), a keepalive that outlives the gaps
    between turns, and a fast connect timeout. Works on openai 1.x-2.x (httpx)
    and 3.x (httpx2): the Limits/Timeout classes come from the SDK itself."""
    Limits = type(openai.DEFAULT_CONNECTION_LIMITS)
    Timeout = type(openai.DEFAULT_TIMEOUT)
    try:
        return openai.DefaultAsyncHttpxClient(
            http2=True,
            limits=Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=300.0),
            timeout=Timeout(60.0, connect=3.0),
            **extra,
        )
    except ImportError:
        raise SystemExit("HTTP/2 needs the h2 package: pip install h2")


def make_client(kind: str, api_key: str, base_url: str, versions: list):
    async def record(response):
        versions.append(response.http_version)

    hooks = {"event_hooks": {"response": [record]}}
    if kind == "http2":
        http = voice_http_client(**hooks)
    else:
        # The SDK's defaults: HTTP/1.1, 5 s keepalive.
        http = openai.DefaultAsyncHttpxClient(**hooks)
    return AsyncOpenAI(api_key=api_key, base_url=base_url, http_client=http)


async def run(kind: str, system: str, tools, model: str, gap: float, base_url: str, cold: bool):
    versions: list = []
    client = make_client(kind, os.environ["HOPPER_API_KEY"], base_url, versions)
    # The random session ID at the TOP of the prompt is deliberate and the one
    # thing a real agent must not copy: it gives each run a prompt nothing has
    # cached yet, so any cache hit below comes from this run's own warm-up.
    messages = [{"role": "system", "content": f"Session {uuid.uuid4()}\n\n{system}"}]
    extra = {"tools": tools} if tools else {}
    if kind == "http2":
        # Connection warm-up: open the HTTP/2 connection (TLS included) before
        # the first turn, as an agent should at process or call start.
        await client.models.list()
        if not cold:
            # Prompt warm-up: one 1-token request with the system prompt and
            # tools puts them in the prompt cache, so even turn 1 is a hit. In
            # production, do this at call start and whenever the prompt changes.
            await client.chat.completions.create(model=model, messages=messages, max_tokens=1, **extra)
    rows = []
    for i, line in enumerate(CALLER_TURNS):
        if i:
            await asyncio.sleep(gap)
        messages.append({"role": "user", "content": line})
        t0 = time.perf_counter()
        ttft, text, calls, usage = None, [], {}, None
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            max_tokens=60,
            temperature=0,
            **extra,
        )
        async for chunk in stream:
            if chunk.usage:
                usage = chunk.usage
            delta = chunk.choices[0].delta if chunk.choices else None
            # Without tools in the request, tool-call deltas can only be parser
            # fragments of a call the model tried to write; they are not speech.
            tool_deltas = (delta.tool_calls or []) if (delta and tools) else []
            if delta and (delta.content or tool_deltas):
                # First token of either kind: spoken text, or the start of a tool call.
                if ttft is None:
                    ttft = (time.perf_counter() - t0) * 1000
                if delta.content:
                    text.append(delta.content)
                for tc in tool_deltas:
                    call = calls.setdefault(tc.index, {"id": tc.id, "name": "", "arguments": ""})
                    call["id"] = tc.id or call["id"]
                    call["name"] += (tc.function.name or "") if tc.function else ""
                    call["arguments"] += (tc.function.arguments or "") if tc.function else ""
        reply = "".join(text)
        calls = {k: c for k, c in calls.items() if c["id"] and c["name"]}
        if calls:
            # Keep the conversation valid: record the call and a stub result.
            messages.append({
                "role": "assistant", "content": reply or None,
                "tool_calls": [{"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"] or "{}"}} for c in calls.values()],
            })
            for c in calls.values():
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": "Tool results are not available in this test."})
            shown = "tool: " + ", ".join(c["name"] for c in calls.values())
        else:
            messages.append({"role": "assistant", "content": reply})
            shown = reply
        details = getattr(usage, "prompt_tokens_details", None)
        cached = (getattr(details, "cached_tokens", None) or 0) if details else 0
        rows.append((i + 1, usage.prompt_tokens, cached, ttft, shown))
    await client.close()
    return rows, versions


LABELS = {
    "http2": "OpenAI SDK, HTTP/2, warm connection + warm prompt cache",
    "http2-cold": "OpenAI SDK, HTTP/2, warm connection, cold prompt (--cold)",
    "defaults": "OpenAI SDK, default client, no warm-up (--baseline)",
}


def report(kind: str, rows, versions, have_tools: bool):
    print(f"\n{LABELS[kind]}: protocol {sorted(set(versions))}")
    print(f"{'turn':>4} {'prompt':>7} {'cached':>7} {'hit':>5} {'ttft_ms':>8}  reply")
    for turn, prompt, cached, ttft, reply in rows:
        shown = f"{ttft:>8.0f}" if ttft is not None else f"{'-':>8}"
        print(f"{turn:>4} {prompt:>7} {cached:>7} {cached / prompt:>5.0%} {shown}  {(reply or '(no text)')[:48]!r}")
    first = {"http2": "prompt cache warmed", "http2-cold": "cold prefill", "defaults": "no warm-up"}[kind]
    hit = sum(r[2] for r in rows) / sum(r[1] for r in rows)
    later = sorted(r[3] for r in rows[1:] if r[3] is not None)
    turn1 = f"{rows[0][3]:.0f} ms" if rows[0][3] is not None else "no text"
    summary = f"turn 1 TTFT {turn1} ({first}) | "
    summary += f"turns 2-10 p50 {statistics.median(later):.0f} ms, max {later[-1]:.0f} ms" if later else "turns 2-10: no text"
    print(summary + f" | cache hit {hit:.0%} across all turns")
    silent = [r[0] for r in rows if r[3] is None]
    if silent:
        hint = "" if have_tools else " The prompt probably calls tools: rerun with --tools tools.json."
        print(f"turns {silent} produced no text and are left out of the TTFT numbers.{hint}")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", help="your agent's system prompt file (default: synthetic ~4k tokens)")
    ap.add_argument("--tools", help="JSON file with the agent's OpenAI-format tools list, sent every turn")
    ap.add_argument("--model", default="gemma-4-31b")
    ap.add_argument("--gap", type=float, default=6.0, help="seconds between turns")
    ap.add_argument("--baseline", action="store_true", help="also run the SDK's default HTTP/1.1 client with no warm-up")
    ap.add_argument("--cold", action="store_true", help="skip the prompt-cache warm-up (worst case: a never-seen prompt)")
    ap.add_argument("--base-url", default="https://api.withhopper.com/v1")
    args = ap.parse_args()
    system = open(args.prompt).read() if args.prompt else synthetic_system_prompt()
    tools = json.load(open(args.tools)) if args.tools else None
    for kind in ["http2"] + (["defaults"] if args.baseline else []):
        rows, versions = await run(kind, system, tools, args.model, args.gap, args.base_url, args.cold)
        report("http2-cold" if kind == "http2" and args.cold else kind, rows, versions, bool(tools))


if __name__ == "__main__":
    asyncio.run(main())

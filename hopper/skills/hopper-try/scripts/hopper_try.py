"""Run prompts on Hopper's open models side by side, with time to first token,
tokens per second and token counts (cost per
answer: the generate tool, or the usage page in the Hopper console). Python standard library only.

    python3 hopper_try.py "Summarize this ticket: ..."
    python3 hopper_try.py --system-file prompt.txt "Where is order 1042?" "I want a refund"
    python3 hopper_try.py --examples examples.json --models deepseek-v4.1-flash,gemma-4-31b
    python3 hopper_try.py --messages-file conversation.json --json
    python3 hopper_try.py --system-file prompt.txt --tools tools.json "Where is order 1042?"

Each positional argument is one example (a user message). --examples takes a JSON
list whose items are strings, {"system", "prompt"} objects, or {"messages": [...]}.
Every example runs on every model, one streamed request each.

The key comes from HOPPER_API_KEY, then ./.env, then ~/.config/hopper/credentials.json
(shared with hopper_voice.py). With none, the first run registers a key for the agent
itself through Hopper's agent registration (https://withhopper.com/auth.md, anonymous
start, small trial credit) and saves it there, mode 600, never in the project. In a
sandbox without network it prints `HOPPER_SANDBOX_BLOCKED …` and exits 3.
"""

import argparse
import contextlib
import http.client
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

AUTH = os.environ.get("HOPPER_AUTH_URL", "https://withhopper.com")
API = os.environ.get("HOPPER_API_URL", "https://api.withhopper.com")
CONFIG = pathlib.Path(
    os.environ.get("HOPPER_CONFIG_DIR")
    or pathlib.Path(os.environ.get("XDG_CONFIG_HOME") or pathlib.Path.home() / ".config") / "hopper"
)
CREDENTIALS = CONFIG / "credentials.json"
REGISTRATION = CONFIG / "registration.json"
MODELS = ["deepseek-v4.1-flash", "gemma-4-31b"]
# Models that think before answering unless told not to.
THINKING_SWITCH = {"deepseek-v4.1-flash": lambda on: {"chat_template_kwargs": {"thinking": on}}}


def fail(message, code=1):
    print(message, file=sys.stderr)
    sys.exit(code)


def in_sandbox():
    return bool(os.environ.get("CODEX_SANDBOX") or os.environ.get("CODEX_SANDBOX_NETWORK_DISABLED"))


def sandbox_blocked(what):
    fail(
        f"HOPPER_SANDBOX_BLOCKED {what}. Hopper needs network access to withhopper.com and "
        f"api.withhopper.com, and write access to {CONFIG}. Rerun this same command with "
        "escalated permissions (network + write).",
        3,
    )


def unreachable(url, error):
    if in_sandbox():
        sandbox_blocked(f"network access to {urllib.parse.urlparse(url).netloc} was refused")
    fail(f"couldn't reach {urllib.parse.urlparse(url).netloc}: {getattr(error, 'reason', error)}")


# --- key: the same agent registration as hopper_trial.py, kept outside the project ---


def write_private(path, text):
    """Create the file mode 600 before any secret is written to it."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)


def post(url, data, form=False):
    body = urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()
    kind = "application/x-www-form-urlencoded" if form else "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, body, {"content-type": kind}), timeout=20) as resp:
            return json.load(resp), resp.status
    except urllib.error.HTTPError as e:
        try:
            return json.load(e), e.code
        except ValueError:
            return {"error": f"HTTP {e.code}"}, e.code
    except (urllib.error.URLError, OSError) as e:
        unreachable(url, e)


def dotenv_key():
    env = pathlib.Path(".env")
    if env.is_file():
        for line in env.read_text().splitlines():
            if line.startswith("HOPPER_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'") or None
    return None


def saved_key():
    if CREDENTIALS.is_file():
        return json.loads(CREDENTIALS.read_text()).get("api_key")
    return None


def register():
    try:
        CONFIG.mkdir(parents=True, exist_ok=True, mode=0o700)
        probe = CONFIG / f".write-test-{os.getpid()}"
        probe.write_text("")
        probe.unlink()
    except OSError:
        if in_sandbox():
            sandbox_blocked(f"writing {CONFIG} was refused")
        fail(f"can't write {CONFIG}; set HOPPER_CONFIG_DIR to a writable folder")
    reg, _ = post(AUTH + "/agent/identity", {"type": "anonymous"})
    if "identity_assertion" not in reg:
        fail(f"Hopper agent registration is unavailable ({reg.get('error')}); see {AUTH}/auth.md")
    grant = {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": reg["identity_assertion"]}
    for _ in range(3):
        tok, status = post(AUTH + "/oauth2/token", grant, form=True)
        if "access_token" in tok or status != 503:
            break
        time.sleep(2)
    if "access_token" not in tok:
        fail(f"getting a trial key failed ({tok.get('error')}); run this again")
    write_private(REGISTRATION, json.dumps({"claim_token": reg["claim_token"]}))
    write_private(CREDENTIALS, json.dumps({"api_key": tok["access_token"], "kind": "trial"}))
    print(f"Got a Hopper trial key for this agent, saved to {CREDENTIALS}.", file=sys.stderr)
    return tok["access_token"]


def api_key():
    return os.environ.get("HOPPER_API_KEY") or dotenv_key() or saved_key() or register()


# --- runs ---


def stream(key, model, messages, max_tokens, temperature, reasoning, tools=None):
    """One streamed chat completion, timed from the request to the first token."""
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if temperature is not None:
        body["temperature"] = temperature
    if tools:
        body["tools"] = tools
    if model in THINKING_SWITCH:
        body.update(THINKING_SWITCH[model](reasoning))
    url = API + "/v1/chat/completions"
    parts = urllib.parse.urlparse(url)
    conn_cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(parts.netloc, timeout=180)
    result = {"model": model, "output": "", "ttft_ms": None, "total_ms": None, "tokens_per_second": None,
              "prompt_tokens": 0, "cached_tokens": 0, "completion_tokens": 0,
              "finish_reason": None, "tool_calls": []}
    try:
        conn.connect()  # TLS handshake before the clock starts: timings are for a warm connection
        start = time.perf_counter()
        conn.request("POST", parts.path, json.dumps(body).encode(),
                     {"content-type": "application/json", "authorization": f"Bearer {key}"})
        resp = conn.getresponse()
    except OSError as e:
        unreachable(url, e)
    first = last = None
    if resp.status >= 400:
        raw = resp.read().decode(errors="replace")
        conn.close()
        try:
            message = json.loads(raw)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = raw[:200]
        if resp.status == 401:
            fail("the Hopper key was rejected (401). If it was moved to an account, use the account key.")
        if resp.status == 402:
            fail("HOPPER_OUT_OF_CREDIT the key has no credit left; the user can create a key on their account at https://withhopper.com/console/keys", 4)
        result["error"] = f"HTTP {resp.status}: {message}"
        return result
    with contextlib.closing(conn):
        for line in resp:
            line = line.strip()
            if not line.startswith(b"data:"):
                continue
            data = line[5:].strip()
            if data == b"[DONE]":
                break
            chunk = json.loads(data)
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                for call in delta.get("tool_calls") or []:
                    now = time.perf_counter()
                    first = first or now
                    last = now
                    index = call.get("index", 0)
                    while len(result["tool_calls"]) <= index:
                        result["tool_calls"].append({"name": "", "arguments": ""})
                    fn = call.get("function") or {}
                    result["tool_calls"][index]["name"] += fn.get("name") or ""
                    result["tool_calls"][index]["arguments"] += fn.get("arguments") or ""
                text = delta.get("content")
                if text:
                    now = time.perf_counter()
                    first = first or now
                    last = now
                    result["output"] += text
                if choice.get("finish_reason"):
                    result["finish_reason"] = choice["finish_reason"]
            usage = chunk.get("usage")
            if usage:
                result["prompt_tokens"] = usage.get("prompt_tokens", 0)
                result["completion_tokens"] = usage.get("completion_tokens", 0)
                result["cached_tokens"] = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    end = time.perf_counter()
    result["total_ms"] = round((end - start) * 1000)
    if first:
        result["ttft_ms"] = round((first - start) * 1000)
        if last > first and result["completion_tokens"] > 1:
            result["tokens_per_second"] = round((result["completion_tokens"] - 1) / (last - first))
    return result


def load_examples(args):
    system = args.system
    if args.system_file:
        system = pathlib.Path(args.system_file).read_text()
    examples = []
    if args.examples:
        for item in json.loads(pathlib.Path(args.examples).read_text()):
            if isinstance(item, str):
                examples.append({"system": system, "prompt": item})
            elif "messages" in item:
                examples.append({"messages": item["messages"]})
            else:
                examples.append({"system": item.get("system", system), "prompt": item["prompt"]})
    if args.messages_file:
        examples.append({"messages": json.loads(pathlib.Path(args.messages_file).read_text())})
    if args.prompt_file:
        examples.append({"system": system, "prompt": pathlib.Path(args.prompt_file).read_text()})
    examples += [{"system": system, "prompt": p} for p in args.prompts]
    if not examples:
        fail("give at least one prompt (positional, --prompt-file, --examples or --messages-file)")
    for example in examples:
        if "messages" not in example:
            msgs = [{"role": "system", "content": example["system"]}] if example.get("system") else []
            example["messages"] = msgs + [{"role": "user", "content": example["prompt"]}]
    return examples


def label(example):
    user = [m for m in example["messages"] if m.get("role") == "user"]
    text = " ".join(str(user[-1]["content"]).split()) if user else "(conversation)"
    return text if len(text) <= 70 else text[:67] + "..."


def main():
    ap = argparse.ArgumentParser(description="Run prompts on Hopper models side by side.")
    ap.add_argument("prompts", nargs="*", help="one or more user messages, each run as its own example")
    ap.add_argument("--system", help="system prompt for every example")
    ap.add_argument("--system-file", help="file holding the system prompt")
    ap.add_argument("--prompt-file", help="file holding one user message")
    ap.add_argument("--examples", help="JSON list of strings, {system, prompt} or {messages} objects")
    ap.add_argument("--messages-file", help="JSON file with one conversation in OpenAI chat format")
    ap.add_argument("--tools", help="JSON file with OpenAI-format tools, sent with every example")
    ap.add_argument("--models", default=",".join(MODELS), help=f"comma-separated; default {','.join(MODELS)}")
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--temperature", type=float)
    ap.add_argument("--reasoning", action="store_true", help="let models that support it think first (default off)")
    ap.add_argument("--json", action="store_true", help="print results as JSON")
    args = ap.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    examples = load_examples(args)
    tools = json.loads(pathlib.Path(args.tools).read_text()) if args.tools else None
    key = api_key()
    runs = []
    for i, example in enumerate(examples, 1):
        for model in models:
            r = stream(key, model, example["messages"], args.max_tokens, args.temperature, args.reasoning, tools)
            r["example"] = i
            runs.append(r)
    if args.json:
        print(json.dumps({"examples": [label(e) for e in examples], "runs": runs}, indent=2))
        return
    for i, example in enumerate(examples, 1):
        print(f"=== Example {i}: {label(example)}")
        for r in (r for r in runs if r["example"] == i):
            if r.get("error"):
                print(f"--- {r['model']}: {r['error']}\n")
                continue
            ttft = f"{r['ttft_ms']} ms" if r["ttft_ms"] is not None else "n/a"
            tps = f"{r['tokens_per_second']} tok/s" if r["tokens_per_second"] else "n/a"
            print(f"--- {r['model']} · TTFT {ttft} · {tps} · {r['prompt_tokens']} in / "
                  f"{r['completion_tokens']} out · finish {r['finish_reason']}")
            for call in r["tool_calls"]:
                try:
                    json.loads(call["arguments"] or "{}")
                    valid = "valid JSON"
                except ValueError:
                    valid = "INVALID JSON"
                print(f"[tool call] {call['name']}({call['arguments']}) · {valid}")
            if r["output"].strip() or not r["tool_calls"]:
                print(r["output"].strip() or "(no text)")
            print()


if __name__ == "__main__":
    main()

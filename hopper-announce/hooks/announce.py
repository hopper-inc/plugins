"""Say one short sentence when a long Claude Code task finishes, with Hopper text-to-speech.

    announce.py start    UserPromptSubmit hook: remember when the turn started
    announce.py stop     Stop hook: if the turn took at least min_seconds, speak its first sentence

Settings live in ~/.config/hopper/announce.json (see skills/hopper-announce). Speech runs in a
detached process, so the hook returns at once and never blocks Claude Code. Errors are
swallowed: an announcement is never worth interrupting the session for.
"""

import json
import os
import pathlib
import re
import subprocess
import sys
import time

CONFIG = pathlib.Path(
    os.environ.get("HOPPER_CONFIG_DIR")
    or pathlib.Path(os.environ.get("XDG_CONFIG_HOME") or pathlib.Path.home() / ".config") / "hopper"
)
SETTINGS = CONFIG / "announce.json"
STARTS = pathlib.Path(os.environ.get("CLAUDE_PLUGIN_DATA") or CONFIG) / "announce-starts.json"
VOICE = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "hopper_voice.py"
DEFAULTS = {"enabled": True, "min_seconds": 20, "voice": None, "max_words": 25}


def settings():
    try:
        return {**DEFAULTS, **json.loads(SETTINGS.read_text())}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def starts():
    try:
        return json.loads(STARTS.read_text())
    except (OSError, ValueError):
        return {}


def save_starts(data):
    STARTS.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    STARTS.write_text(json.dumps({k: v for k, v in data.items() if now - v < 86_400}))


def sentence(text, max_words):
    """The first sentence of the reply, as it would be said: no code blocks, links or Markdown."""
    text = re.sub(r"```.*?```", "\n", text, flags=re.S)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s*#.*$", "", text, flags=re.M)  # headings aren't sentences
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"https?://\S+|[*_#>|]+", "", text)
    lines = [re.sub(r"^\s*(?:[-•]|\d+[.)])\s+", "", line).strip() for line in text.splitlines()]
    first = next((line for line in lines if line), "Done.")
    first = re.split(r"(?<=[.!?])\s", first, maxsplit=1)[0]
    words = first.split()
    return " ".join(words[:max_words]) + ("…" if len(words) > max_words else "")


def main():
    event = json.load(sys.stdin)
    session = event.get("session_id", "default")
    data = starts()
    if sys.argv[1] == "start":
        data[session] = time.time()
        save_starts(data)
        return
    config = settings()
    began = data.pop(session, None)
    save_starts(data)
    if event.get("stop_hook_active") or not config["enabled"] or began is None:
        return
    if time.time() - began < config["min_seconds"]:
        return
    args = [sys.executable, str(VOICE), "speak", sentence(event.get("last_assistant_message") or "", config["max_words"]), "--play"]
    if config["voice"]:
        args += ["--voice", config["voice"]]
    subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

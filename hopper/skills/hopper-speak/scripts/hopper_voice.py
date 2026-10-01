"""Hopper text to speech and speech to text for an agent's own use.

    python3 hopper_voice.py speak "Text to say" [--voice elena] [--out speech.wav] [--play]
    python3 hopper_voice.py speak --file notes.md [--out notes.wav]
    python3 hopper_voice.py transcribe recording.m4a [--json]
    python3 hopper_voice.py voices
    python3 hopper_voice.py claim user@example.com [--no-wait]
    python3 hopper_voice.py status

The key comes from HOPPER_API_KEY, then ./.env, then ~/.config/hopper/credentials.json.
With none, this registers a trial key ($2 credit, no sign-up) through Hopper's agent
registration (https://withhopper.com/auth.md) and saves it to ~/.config/hopper/
(mode 600), never to the project. `claim` moves that key to the user's own account:
it prints a link and a 6-digit code, then waits for them to enter it.

Python standard library only. `transcribe` uses ffmpeg to decode anything that isn't
16-bit PCM WAV. Keys are never printed.

When a trial key runs low (under $0.50) the script prints one line to stderr,
`HOPPER_HANDOVER low_credit …`, with what Hopper has done so far; when it runs out
(402) it prints `HOPPER_HANDOVER out_of_credit …` and exits 4. The agent then tells
the user and offers `claim`. In a sandbox that blocks network or ~/.config, it prints
`HOPPER_SANDBOX_BLOCKED …` and exits 3 before doing anything.

Exit codes: 0 ok · 1 error · 2 the claim code expired (run claim again) ·
3 blocked by the sandbox (rerun with network and write access) · 4 out of trial credit.
"""

import argparse
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import wave

AUTH = os.environ.get("HOPPER_AUTH_URL", "https://withhopper.com")
API = os.environ.get("HOPPER_API_URL", "https://api.withhopper.com")
CONFIG = pathlib.Path(
    os.environ.get("HOPPER_CONFIG_DIR")
    or pathlib.Path(os.environ.get("XDG_CONFIG_HOME") or pathlib.Path.home() / ".config") / "hopper"
)
CREDENTIALS = CONFIG / "credentials.json"
REGISTRATION = CONFIG / "registration.json"
CLAIM_GRANT = "urn:workos:agent-auth:grant-type:claim"
USAGE = CONFIG / "usage.json"
LOW_CREDIT_USD = 0.50
LAST = {"credits": None}  # x-hopper-credits-remaining-usd from the last response
TTS_MODEL, TTS_LIMIT = "qwen3-tts", 1000  # characters per request
STT_MODEL, STT_LIMIT = "nemotron-asr", 24_000_000  # bytes per upload (the API takes 25 MB)


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def write_private(path, text):
    """Create the file mode 600 before any secret is written to it."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)


def in_sandbox():
    return bool(os.environ.get("CODEX_SANDBOX") or os.environ.get("CODEX_SANDBOX_NETWORK_DISABLED"))


def sandbox_blocked(what):
    """Say exactly what the sandbox blocked and how to proceed, then exit 3."""
    print(
        f"HOPPER_SANDBOX_BLOCKED {what}. Hopper needs network access to withhopper.com and "
        f"api.withhopper.com, and write access to {CONFIG}. Rerun this same command with "
        "escalated permissions (network + write).",
        file=sys.stderr,
    )
    sys.exit(3)


def config_writable():
    try:
        CONFIG.mkdir(parents=True, exist_ok=True, mode=0o700)
        probe = CONFIG / f".write-test-{os.getpid()}"
        probe.write_text("")
        probe.unlink()
        return True
    except OSError:
        return False


def http(url, data=None, headers=None, form=False, raw=False, timeout=120):
    """POST (with data) or GET; returns parsed JSON (or bytes with raw) and never raises on HTTP errors."""
    headers = dict(headers or {})
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()
        headers["content-type"] = "application/x-www-form-urlencoded" if form else "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data, headers), timeout=timeout) as resp:
            body = resp.read()
            credits = resp.headers.get("x-hopper-credits-remaining-usd")
            if credits:
                try:
                    LAST["credits"] = float(credits)
                except ValueError:
                    pass
            return (body if raw else json.loads(body)), resp.status
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return json.loads(body), e.code
        except ValueError:
            return {"error": {"message": body[:200].decode(errors="replace")}}, e.code
    except (urllib.error.URLError, OSError) as e:
        if in_sandbox():
            sandbox_blocked(f"network access to {urllib.parse.urlparse(url).netloc} was refused")
        fail(f"couldn't reach {urllib.parse.urlparse(url).netloc}: {getattr(e, 'reason', e)}")


def error_text(body):
    err = body.get("error") if isinstance(body, dict) else None
    if isinstance(err, dict):
        return err.get("message") or err.get("code") or json.dumps(err)
    return body.get("error_description") or err or "unknown error"


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
    # Check before registering: a key minted but not saved is lost along with its claim.
    if not config_writable():
        if in_sandbox():
            sandbox_blocked(f"writing {CONFIG} was refused")
        fail(f"can't write {CONFIG}; set HOPPER_CONFIG_DIR to a writable folder")
    reg, _ = http(AUTH + "/agent/identity", {"type": "anonymous"})
    if "identity_assertion" not in reg:
        fail(f"Hopper agent registration is unavailable ({reg.get('error')}); see {AUTH}/auth.md")
    grant = {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": reg["identity_assertion"]}
    for _ in range(3):
        tok, status = http(AUTH + "/oauth2/token", grant, form=True)
        if "access_token" in tok or status != 503:
            break
        time.sleep(2)
    if "access_token" not in tok:
        fail(f"getting a trial key failed ({tok.get('error')}); run this again")
    write_private(REGISTRATION, json.dumps({"claim_token": reg["claim_token"]}))
    write_private(CREDENTIALS, json.dumps({"api_key": tok["access_token"], "kind": "trial"}))
    print(f"Got a Hopper trial key, saved to {CREDENTIALS}. Run `claim` to keep it.", file=sys.stderr)
    return tok["access_token"]


def api_key():
    return os.environ.get("HOPPER_API_KEY") or dotenv_key() or saved_key() or register()


def auth_headers():
    return {"Authorization": f"Bearer {api_key()}"}


def check(body, status, what):
    if status == 401:
        fail(f"{what} failed: the key was rejected (401). If it was claimed, the trial key no longer works.")
    if status == 402:
        if is_trial():
            print(f"HOPPER_HANDOVER out_of_credit used=\"{usage_summary()}\" next=\"claim <email>\"", file=sys.stderr)
            sys.exit(4)
        fail(f"{what} failed: the account is out of credit; add credits at https://withhopper.com/console/billing.")
    if status >= 400:
        fail(f"{what} failed ({status}): {error_text(body)}")


def is_trial():
    """The key in use is this agent's own trial key (claimable), not a project or account key."""
    if os.environ.get("HOPPER_API_KEY") or dotenv_key():
        return False
    return REGISTRATION.is_file()


def record_usage(kind, seconds):
    if not is_trial():
        return
    try:
        data = json.loads(USAGE.read_text()) if USAGE.is_file() else {}
    except (OSError, ValueError):
        data = {}
    data.setdefault("since", time.strftime("%Y-%m-%d"))
    data[kind] = round(data.get(kind, 0) + seconds, 1)
    data["calls"] = data.get("calls", 0) + 1
    try:
        write_private(USAGE, json.dumps(data))
    except OSError:
        pass


def usage_summary():
    try:
        data = json.loads(USAGE.read_text())
    except (OSError, ValueError):
        return "no usage recorded yet"
    def amount(seconds):
        return f"{seconds:.0f} s" if seconds < 60 else f"{seconds / 60:.1f} min"

    parts = []
    if data.get("transcribe"):
        parts.append(f"{amount(data['transcribe'])} transcribed")
    if data.get("speak"):
        parts.append(f"{amount(data['speak'])} of speech")
    return f"{', '.join(parts) or 'no audio yet'} in {data.get('calls', 0)} calls since {data.get('since')}"


def maybe_handover():
    """Once the trial key is low, tell the agent (stderr) so it can offer the user the claim."""
    credits = LAST["credits"]
    if is_trial() and credits is not None and credits < LOW_CREDIT_USD:
        print(
            f"HOPPER_HANDOVER low_credit credits_left=${credits:.2f} used=\"{usage_summary()}\" next=\"claim <email>\"",
            file=sys.stderr,
        )


# --- voices


def list_voices():
    body, status = http(API + "/voices?scope=featured", headers=auth_headers())
    check(body, status, "listing voices")
    return [v for v in body["voices"] if any(p["model_id"] == TTS_MODEL and p["status"] == "ready" for p in v["profiles"])]


def pick_voice(wanted):
    voices = list_voices()
    if not voices:
        fail("no voices are ready right now; try again in a minute")
    if not wanted:
        # A neutral default: the first conversational General American voice, else the first ready one.
        neutral = [v for v in voices if {"conversational", "accent:general american"} <= set(v.get("tags") or [])]
        return (neutral or voices)[0]
    for v in voices:
        if wanted.lower() in (v["id"].lower(), (v.get("name") or "").lower()):
            return v
    fail(f"no ready voice named {wanted!r}; run `voices` to list them")


# --- speak


def chunks(text, limit=TTS_LIMIT):
    """Split on sentence ends, then on spaces, so every request fits the model's limit."""
    text = re.sub(r"\s+", " ", text).strip()
    out, current = [], ""
    for sentence in re.split(r"(?<=[.!?;:])\s+", text):
        while len(sentence) > limit:
            cut = sentence.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            if current:
                out.append(current)
                current = ""
            out.append(sentence[:cut])
            sentence = sentence[cut:].lstrip()
        if len(current) + len(sentence) + 1 > limit:
            out.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        out.append(current)
    return out


def synthesize(text, voice_id):
    frames, params = [], None
    for part in chunks(text):
        audio, status = http(
            API + "/v1/audio/speech",
            {"model": TTS_MODEL, "voice": voice_id, "input": part, "response_format": "wav"},
            headers=auth_headers(),
            raw=True,
        )
        check(audio if isinstance(audio, dict) else {}, status, "speech")
        with wave.open(io.BytesIO(audio)) as w:
            params = params or w.getparams()
            frames.append(w.readframes(w.getnframes()))
    return params, b"".join(frames)


def player():
    for cmd in (["afplay"], ["paplay"], ["aplay", "-q"], ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]):
        if shutil.which(cmd[0]):
            return cmd
    return None


def speak(args):
    text = pathlib.Path(args.file).read_text() if args.file else " ".join(args.text)
    if not text.strip():
        fail("nothing to say: pass text or --file")
    if len(text) > args.max_chars:
        fail(f"text is {len(text)} characters; pass --max-chars {len(text)} to confirm (about $0.005 per 1,000)")
    voice = pick_voice(args.voice)
    params, frames = synthesize(text, voice["id"])
    out = pathlib.Path(args.out) if args.out else None
    if out is None:
        out = pathlib.Path(tempfile.gettempdir()) / f"hopper-speech-{uuid.uuid4().hex[:8]}.wav" if args.play else pathlib.Path("speech.wav")
    with wave.open(str(out), "wb") as w:
        w.setparams(params)
        w.writeframes(frames)
    seconds = len(frames) / (params.sampwidth * params.nchannels * params.framerate)
    record_usage("speak", seconds)
    print(json.dumps({"file": str(out), "seconds": round(seconds, 2), "voice": voice["id"]}))
    maybe_handover()
    if args.play:
        cmd = player()
        if not cmd:
            fail(f"no audio player found (afplay, paplay, aplay, ffplay); the audio is in {out}")
        subprocess.run(cmd + [str(out)], check=False)
        if not args.out:
            out.unlink(missing_ok=True)


# --- transcribe


def as_pcm(path):
    """Mono 16-bit PCM samples and their rate; decodes other formats with ffmpeg."""
    try:
        with wave.open(str(path)) as w:
            if w.getsampwidth() == 2 and w.getnchannels() == 1:
                return w.readframes(w.getnframes()), w.getframerate()
    except (wave.Error, EOFError):
        pass
    if not shutil.which("ffmpeg"):
        fail(f"{path.name} isn't 16-bit mono WAV; install ffmpeg to decode it (brew install ffmpeg / apt install ffmpeg)")
    decoded = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
        capture_output=True,
    )
    if decoded.returncode != 0 or not decoded.stdout:
        fail(f"ffmpeg couldn't decode {path.name}: {decoded.stderr.decode(errors='replace').strip()[:300] or 'no audio track'}")
    return decoded.stdout, 16000


def wav_segments(pcm, rate, limit=STT_LIMIT):
    """WAV uploads under the size limit; yields (wav bytes, offset seconds)."""
    step = (limit - 1024) // 2 * 2
    for start in range(0, len(pcm), step):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(rate)
            out.writeframes(pcm[start : start + step])
        yield buf.getvalue(), start / 2 / rate


def multipart(fields, filename, content):
    boundary = uuid.uuid4().hex
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
        + content
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def transcribe(args):
    path = pathlib.Path(args.file)
    if not path.is_file():
        fail(f"no such file: {path}")
    pcm, rate = as_pcm(path)
    texts, words, seconds = [], [], 0.0
    for segment, offset in wav_segments(pcm, rate):
        body, ctype = multipart({"model": STT_MODEL, "sample_rate": rate}, "audio.wav", segment)
        result, status = http(API + "/v1/audio/transcriptions", body, headers={**auth_headers(), "content-type": ctype}, timeout=300)
        check(result, status, "transcription")
        texts.append(result.get("text", "").strip())
        words += [
            dict(w, text=w["text"].strip(), start=round(w["start"] + offset, 3), end=round(w["end"] + offset, 3))
            for w in result.get("words", [])
        ]
        seconds += result.get("duration_seconds", 0.0)
    text = " ".join(t for t in texts if t)
    record_usage("transcribe", seconds)
    maybe_handover()
    if not text:
        print(f"no speech detected in {path.name}", file=sys.stderr)
    if args.json:
        print(json.dumps({"text": text, "words": words, "duration_seconds": round(seconds, 3)}))
    else:
        print(text)


# --- account


def claim(args):
    if not REGISTRATION.is_file():
        fail("no trial registration to claim; this key is already on an account, or came from somewhere else")
    state = json.loads(REGISTRATION.read_text())
    attempt = state.get("attempt")
    if not attempt or attempt.get("email") != args.email or attempt["expires_at"] <= time.time() + 30:
        started, _ = http(AUTH + "/agent/identity/claim", {"claim_token": state["claim_token"], "email": args.email})
        if "claim_attempt" not in started:
            fail(f"could not start the claim ({started.get('error')}): {started.get('error_description')}")
        attempt = dict(started["claim_attempt"], email=args.email, expires_at=time.time() + started["claim_attempt"]["expires_in"])
        write_private(REGISTRATION, json.dumps(dict(state, attempt=attempt)))
    print("Link:", attempt["verification_uri"], flush=True)
    print("Code:", attempt["user_code"], flush=True)
    if args.no_wait:
        return
    while time.time() < attempt["expires_at"] + 30:
        time.sleep(attempt["interval"])
        result, _ = http(AUTH + "/oauth2/token", {"grant_type": CLAIM_GRANT, "claim_token": state["claim_token"]}, form=True)
        if "access_token" in result:
            write_private(CREDENTIALS, json.dumps({"api_key": result["access_token"], "kind": "account"}))
            REGISTRATION.unlink(missing_ok=True)
            print(f"Claimed: the key in {CREDENTIALS} is now on the user's account. The trial key no longer works.")
            return
        if result.get("error") == "expired_token":
            break
        if result.get("error") not in ("authorization_pending", "slow_down", "temporarily_unavailable"):
            fail(f"claim failed ({result.get('error')}): {result.get('error_description')}")
    print("The code expired before it was used; run claim again for a new one.")
    sys.exit(2)


def status(_args):
    source = (
        "HOPPER_API_KEY" if os.environ.get("HOPPER_API_KEY") else ".env" if dotenv_key()
        else str(CREDENTIALS) if saved_key() else None
    )
    kind = json.loads(CREDENTIALS.read_text()).get("kind") if source == str(CREDENTIALS) else None
    print(json.dumps({"key": source, "kind": kind, "claimable": REGISTRATION.is_file()}))


def main():
    ap = argparse.ArgumentParser(description="Hopper text to speech and speech to text")
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("speak", help="turn text into speech")
    s.add_argument("text", nargs="*")
    s.add_argument("--file", help="read the text from a file")
    s.add_argument("--voice", help="voice id or name (default: a neutral conversational voice; see `voices`)")
    s.add_argument("--out", help="write the WAV here (default: speech.wav, or a temp file with --play)")
    s.add_argument("--play", action="store_true", help="play it through the speakers")
    s.add_argument("--max-chars", type=int, default=4000, help="refuse longer text unless raised")
    s.set_defaults(run=speak)
    t = sub.add_parser("transcribe", help="turn an audio or video file into text")
    t.add_argument("file")
    t.add_argument("--json", action="store_true", help="print text, word timestamps and duration as JSON")
    t.set_defaults(run=transcribe)
    sub.add_parser("voices", help="list ready voices").set_defaults(
        run=lambda _: print(json.dumps([{"id": v["id"], "description": v.get("description"), "gender": v.get("gender"), "tags": v.get("tags")} for v in list_voices()], indent=1))
    )
    c = sub.add_parser("claim", help="move the trial key to the user's account")
    c.add_argument("email")
    c.add_argument("--no-wait", action="store_true", help="print the link and code, then exit")
    c.set_defaults(run=claim)
    sub.add_parser("status", help="where the key comes from (never prints it)").set_defaults(run=status)
    args = ap.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()

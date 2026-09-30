"""Move a Hopper trial key to the user's own account.

Starts the claim for the registration hopper_trial.py saved, prints the link
and 6-digit code for the user (first two lines, printed immediately), then
waits for them to confirm it in the browser. When they do, it writes the
account key to ./.env as HOPPER_API_KEY (the trial key stops working at that
moment; restart any running agent process) and deletes the saved registration.
Python standard library only.

    python3 hopper_claim.py user@example.com            # prints link + code, then waits
    python3 hopper_claim.py user@example.com --no-wait  # prints link + code, exits
    python3 hopper_claim.py user@example.com            # later: resumes waiting on the SAME code

Rerunning reuses the pending link and code until they expire (10 minutes), so
an agent that can't block can print them, return, and come back to wait.

Exit codes: 0 key saved (or link printed with --no-wait) · 1 error ·
2 the code expired before it was used; run again for a new one.
"""

import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("HOPPER_AUTH_URL", "https://withhopper.com")
STATE = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "hopper-registration.json"
CLAIM_GRANT = "urn:workos:agent-auth:grant-type:claim"


def post(path, data, form=False):
    body = urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()
    kind = "application/x-www-form-urlencoded" if form else "application/json"
    req = urllib.request.Request(BASE + path, body, {"content-type": kind})
    try:
        return json.load(urllib.request.urlopen(req, timeout=20))
    except urllib.error.HTTPError as e:
        return json.load(e)


def write_private(path, text):
    """Create the file mode 600 before any secret is written to it."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)


def save_key(key, env=pathlib.Path(".env")):
    lines = [l for l in (env.read_text().splitlines() if env.exists() else []) if not l.startswith("HOPPER_API_KEY=")]
    env.write_text("\n".join(lines + [f"HOPPER_API_KEY={key}"]) + "\n")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        raise SystemExit(__doc__)
    if not STATE.exists():
        raise SystemExit("no saved registration; run hopper_trial.py first")
    state = json.loads(STATE.read_text())
    claim_token = state["claim_token"]

    attempt = state.get("attempt")
    if not attempt or attempt.get("email") != args[0] or attempt["expires_at"] <= time.time() + 30:
        started = post("/agent/identity/claim", {"claim_token": claim_token, "email": args[0]})
        if "claim_attempt" not in started:
            raise SystemExit(f"could not start the claim ({started.get('error')}): {started.get('error_description')}")
        attempt = dict(started["claim_attempt"], email=args[0], expires_at=time.time() + started["claim_attempt"]["expires_in"])
        write_private(STATE, json.dumps(dict(state, attempt=attempt)))
    print("Link:", attempt["verification_uri"], flush=True)
    print("Code:", attempt["user_code"], flush=True)
    if "--no-wait" in sys.argv:
        return

    deadline = attempt["expires_at"] + 30
    while time.time() < deadline:
        time.sleep(attempt["interval"])
        result = post("/oauth2/token", {"grant_type": CLAIM_GRANT, "claim_token": claim_token}, form=True)
        if "access_token" in result:
            save_key(result["access_token"])
            STATE.unlink(missing_ok=True)
            print("Claimed: account key saved to .env as HOPPER_API_KEY. The trial key no longer works;")
            print("restart any running agent process so it loads the new key.")
            return
        error = result.get("error")
        if error == "expired_token":
            print("The code expired before it was used; run this again for a new one.")
            sys.exit(2)
        if error not in ("authorization_pending", "slow_down", "temporarily_unavailable"):
            raise SystemExit(f"claim failed ({error}): {result.get('error_description')}")
    print("The code expired before it was used; run this again for a new one.")
    sys.exit(2)


if __name__ == "__main__":
    main()

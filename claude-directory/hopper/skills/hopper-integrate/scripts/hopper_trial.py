"""Get a Hopper trial key for this project, with no sign-up.

Registers through Hopper's agent registration (https://withhopper.com/auth.md,
anonymous start), writes HOPPER_API_KEY to ./.env without printing it, and
keeps the registration in a private temp file so hopper_claim.py can move the
key to the user's own account later. Python standard library only.

    python3 hopper_trial.py
"""

import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("HOPPER_AUTH_URL", "https://withhopper.com")
STATE = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "hopper-registration.json"


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
    reg = post("/agent/identity", {"type": "anonymous"})
    if "identity_assertion" not in reg:
        raise SystemExit(f"anonymous start unavailable ({reg.get('error')}); use service_auth in {BASE}/auth.md")
    tok = post(
        "/oauth2/token",
        {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": reg["identity_assertion"]},
        form=True,
    )
    if "access_token" not in tok:
        raise SystemExit(f"token exchange failed ({tok.get('error')}); run this again")
    write_private(STATE, json.dumps({"claim_token": reg["claim_token"]}))
    save_key(tok["access_token"])
    print("HOPPER_API_KEY saved to .env (trial key, $2 credit). Keep .env out of git.")


if __name__ == "__main__":
    main()

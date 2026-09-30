"""Show or change hopper-announce settings (~/.config/hopper/announce.json).

    python3 settings.py                     show
    python3 settings.py enabled=false       stop announcing (enabled=true to resume)
    python3 settings.py min_seconds=60      only for tasks that take a minute or more
    python3 settings.py voice=hudson        another voice (voice= for the default)
    python3 settings.py max_words=15        shorter announcements
"""

import json
import os
import pathlib
import sys

CONFIG = pathlib.Path(
    os.environ.get("HOPPER_CONFIG_DIR")
    or pathlib.Path(os.environ.get("XDG_CONFIG_HOME") or pathlib.Path.home() / ".config") / "hopper"
)
SETTINGS = CONFIG / "announce.json"
DEFAULTS = {"enabled": True, "min_seconds": 20, "voice": None, "max_words": 25}

current = dict(DEFAULTS)
if SETTINGS.exists():
    current.update(json.loads(SETTINGS.read_text()))
for arg in sys.argv[1:]:
    key, _, value = arg.partition("=")
    if key not in DEFAULTS:
        raise SystemExit(f"unknown setting {key!r}; one of {', '.join(DEFAULTS)}")
    if key == "enabled":
        current[key] = value.lower() in ("1", "true", "on", "yes")
    elif key in ("min_seconds", "max_words"):
        current[key] = max(0, int(value))
    else:
        current[key] = value or None
if sys.argv[1:]:
    SETTINGS.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    SETTINGS.write_text(json.dumps(current, indent=1) + "\n")
print(json.dumps(current))

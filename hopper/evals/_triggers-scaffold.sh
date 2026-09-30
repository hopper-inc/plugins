#!/bin/bash
# Workspace for the trigger test: the Pipecat agent plus the audio files the prompts name.
set -e
cp -R "$(dirname "$0")/_fixtures/pipecat/." .
python3 - <<'PY'
import wave
for name in ("voicemail.wav", "call.wav"):
    with wave.open(name, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b"\0\0" * 16000)
PY
cp call.wav standup.m4a
git init -q && git add -A && git -c user.email=dev@example.com -c user.name=Dev commit -qm "voice agent"

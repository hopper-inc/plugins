---
name: hopper-speak
description: 'Turn text into speech with Hopper text-to-speech: play it aloud, save a WAV file, or preview and pick a voice. Works right away with no account; the first use registers a trial key for the agent itself. Use when the user says "read this aloud", "say this out loud", "generate a voiceover", "make an audio file of…", "TTS" or "which voice should I use". Not for writing a speech (plain text), transcribing audio (hopper-transcribe) or a voice agent''s LLM (hopper-integrate).'
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_voice.py *)
---

# Speak with Hopper

`${CLAUDE_SKILL_DIR}` is the folder holding this file (if your host doesn't fill it in, use that folder's absolute path). The script needs network access to `withhopper.com` and `api.withhopper.com`, and writes its key to `~/.config/hopper/`; if the sandbox blocks either, ask for approval. Explicit instructions from the user override these steps.

## Say it

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_voice.py speak "Text to say" --play               # play it now
python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_voice.py speak --file notes.md --out notes.wav     # save a file
```

- It prints `{"file", "seconds", "voice"}`. Tell the user the file and length, in one line.
- **Play or save:** "read this aloud" and "say it" mean `--play`; "make an audio file" means `--out <name>.wav`. Without either, it writes `speech.wav` in the current folder.
- **Text:** speak what the user asked for, as they'd hear it: drop Markdown symbols, code blocks and URLs unless they asked for them read out. Long text is split and joined automatically; over 4,000 characters it stops and asks for `--max-chars` so a long read is never a surprise (about $0.005 per 1,000 characters).
- **Voices:** `voices` lists ids with descriptions, tags and gender. Pick by id or name with `--voice`. The default is a neutral conversational American voice. For a preview, say one short sentence in two or three candidate voices.
- Audio is 24 kHz mono WAV. English is the tested language.

## Key

The first run with no `HOPPER_API_KEY` (environment or the project's `.env`) registers a trial key ($2 credit, no sign-up, [agent registration](https://withhopper.com/auth.md)) and saves it to `~/.config/hopper/credentials.json`, mode 600. Never print it or copy it into the project. `status` says where the key comes from without showing it.

To keep using it past the trial, ask for the user's email and run `claim <email>` in the background: it prints a link and a 6-digit code for the user, then waits (`--no-wait` prints and exits; run it again to resume). A 402 means the credit ran out: offer the claim, or the [console](https://withhopper.com/console) to top up.

## In a voice agent's code

To add Hopper text-to-speech to an application rather than speak now, follow https://docs.withhopper.com/tts: `POST https://api.withhopper.com/v1/audio/speech` with `model: qwen3-tts`, a voice id, `input` up to 1,000 characters, and `stream: true` for the lowest time to first audio.

---
name: hopper-transcribe
description: 'Transcribe speech in an audio or video file with Hopper speech-to-text, with word timestamps. Takes WAV, MP3, M4A, voice memos and video (decoded with ffmpeg). Works right away with no account; the first use registers a trial key for the agent itself. Use when the user says "transcribe this", "what does this recording say", "speech to text", "STT", "summarize this call" or "caption this". Not for generating audio (hopper-speak) or measuring LLM latency (hopper-benchmark).'
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_voice.py *)
---

# Transcribe with Hopper

`${CLAUDE_SKILL_DIR}` is the folder holding this file (if your host doesn't fill it in, use that folder's absolute path). The script needs network access to `withhopper.com` and `api.withhopper.com`, and writes its key to `~/.config/hopper/`; if the sandbox blocks either, ask for approval. Explicit instructions from the user override these steps.

## Transcribe

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_voice.py transcribe path/to/recording.m4a          # plain text
python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_voice.py transcribe call.wav --json                # text, words with start/end seconds
```

- **Formats:** 16-bit mono WAV goes up as is. Anything else (MP3, M4A, AIFF, FLAC, MP4, MOV) is decoded with `ffmpeg`; if it's missing, tell the user the one install command the script prints.
- **Length:** long recordings are split into uploads under the 25 MB limit and the timestamps are joined back, so any length works; it's about $0.05 per hour of audio.
- **A URL:** download it to a temp file first, then transcribe the file.
- **Output:** answer what the user asked (a summary, action items, a quote) from the transcript, and quote it exactly when they want exact words. Use `--json` for captions, timestamps or who-said-when questions. The model writes lowercase text without punctuation, English only, and can mishear names and brands: say so when a name matters.
- `no speech detected` means the file has no audible speech, not an error.

## Key

The first run with no `HOPPER_API_KEY` (environment or the project's `.env`) registers a trial key ($2 credit, no sign-up, [agent registration](https://withhopper.com/auth.md)) and saves it to `~/.config/hopper/credentials.json`, mode 600. Never print it or copy it into the project. `status` says where the key comes from without showing it.

To keep using it past the trial, ask for the user's email and run `claim <email>` in the background: it prints a link and a 6-digit code for the user, then waits (`--no-wait` prints and exits; run it again to resume). A 402 means the credit ran out: offer the claim, or the [console](https://withhopper.com/console) to top up.

## In a voice agent's code

To add Hopper speech-to-text to an application, follow https://docs.withhopper.com/stt: `POST https://api.withhopper.com/v1/audio/transcriptions` (`model: nemotron-asr`, 16-bit PCM or WAV) for files, or the WebSocket stream for live audio.

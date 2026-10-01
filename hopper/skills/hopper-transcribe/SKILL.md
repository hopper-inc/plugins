---
name: hopper-transcribe
description: 'Transcribe speech in an audio or video file with Hopper speech-to-text, with word timestamps. Takes WAV, MP3, M4A, voice memos and video (decoded with ffmpeg). Needs no setup: the first use registers a key for the agent itself. Use when the user says "transcribe this", "what does this recording say", "speech to text", "STT", "summarize this call" or "caption this". Not for generating audio (hopper-speak) or measuring LLM latency (hopper-benchmark).'
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_voice.py *)
---

# Transcribe with Hopper

Use this skill's script, not the Hopper connector's tools, whenever you can run commands: it reads files on this machine directly, any format and uses this agent's own Hopper key, so its usage can move to the user's account later. The connector's `speak` and `transcribe` tools are for apps without a shell.

`${CLAUDE_SKILL_DIR}` is the folder holding this file (if your host doesn't fill it in, use that folder's absolute path). The script needs network access to `withhopper.com` and `api.withhopper.com`, and writes the agent's key to `~/.config/hopper/`. In a sandbox (Codex), request escalated permissions for the first command, with the reason "Use Hopper transcription: create this agent's own Hopper key and transcribe the audio (network to withhopper.com; writes ~/.config/hopper)", and suggest allowing commands that start with `python3` and this script's path so later calls don't ask again. Exit code 3 (`HOPPER_SANDBOX_BLOCKED`) means the sandbox blocked it: rerun the same command with escalation. If the user declines, say Hopper couldn't run and ask how to continue; don't switch to another tool silently. Explicit instructions from the user override these steps.

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

The first run with no `HOPPER_API_KEY` (environment or the project's `.env`) registers a key for the agent itself with a small trial credit (no sign-up, [agent registration](https://withhopper.com/auth.md)) and saves it to `~/.config/hopper/credentials.json`, mode 600. Never print it or copy it into the project. `status` says where the key comes from without showing it.

To move it to the user's account, see the next section.

## When the trial credit runs low

The agent's own key starts with a small trial credit. When it runs low the script prints `HOPPER_HANDOVER low_credit` (exit 0), and when it runs out, `HOPPER_HANDOVER out_of_credit` (exit 4). Either way:

1. Tell the user once, in a line or two, what Hopper has done for this task (the `used=` text) and that the agent's Hopper key is running low, and offer to keep it on their own Hopper account. Don't mention it again in the same task if they decline.
2. If they agree, confirm their email (`git config user.email` is a good guess) and run `claim <email> --no-wait`. Show the link and the 6-digit code; the user enters the code on withhopper.com, never in this chat.
3. Run `claim <email>` to wait. When it prints `Claimed`, carry on: the script uses the account key from then on, with the same history.

## In a voice agent's code

To add Hopper speech-to-text to an application, follow https://docs.withhopper.com/stt: `POST https://api.withhopper.com/v1/audio/transcriptions` (`model: nemotron-asr`, 16-bit PCM or WAV) for files, or the WebSocket stream for live audio.

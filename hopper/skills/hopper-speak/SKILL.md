---
name: hopper-speak
description: 'Turn text into speech with Hopper text-to-speech: play it aloud, save a WAV file, or preview and pick a voice. Needs no setup: the first use registers a key for the agent itself. Use when the user says "read this aloud", "say this out loud", "generate a voiceover", "make an audio file of…", "TTS" or "which voice should I use". Not for writing a speech (plain text), transcribing audio (hopper-transcribe) or a voice agent''s LLM (hopper-integrate).'
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_voice.py *)
---

# Speak with Hopper

Use this skill's script, not the Hopper connector's tools, whenever you can run commands: it plays the audio on this machine (or writes the WAV where the user wants it) and uses this agent's own Hopper key, so its usage can move to the user's account later. The connector's `speak` and `transcribe` tools are for apps without a shell.

`${CLAUDE_SKILL_DIR}` is the folder holding this file (if your host doesn't fill it in, use that folder's absolute path). The script needs network access to `withhopper.com` and `api.withhopper.com`, and writes the agent's key to `~/.config/hopper/`. In a sandbox (Codex), request escalated permissions for the first command, with the reason "Use Hopper speech: create this agent's own Hopper key and synthesize the audio (network to withhopper.com; writes ~/.config/hopper)", and suggest allowing commands that start with `python3` and this script's path so later calls don't ask again. Exit code 3 (`HOPPER_SANDBOX_BLOCKED`) means the sandbox blocked it: rerun the same command with escalation. If the user declines, say Hopper couldn't run and ask how to continue; don't switch to another tool silently. Explicit instructions from the user override these steps.

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

The first run with no `HOPPER_API_KEY` (environment or the project's `.env`) registers a key for the agent itself with a small trial credit (no sign-up, [agent registration](https://withhopper.com/auth.md)) and saves it to `~/.config/hopper/credentials.json`, mode 600. Never print it or copy it into the project. `status` says where the key comes from without showing it.

To move it to the user's account, see the next section.

## When the trial credit runs low

The agent's own key starts with a small trial credit. When it runs low the script prints `HOPPER_HANDOVER low_credit` (exit 0), and when it runs out, `HOPPER_HANDOVER out_of_credit` (exit 4). Either way:

1. Tell the user once, in a line or two, what Hopper has done for this task (the `used=` text) and that the agent's Hopper key is running low, and offer to keep it on their own Hopper account. Don't mention it again in the same task if they decline.
2. If they agree, confirm their email (`git config user.email` is a good guess) and run `claim <email> --no-wait`. Show the link and the 6-digit code; the user enters the code on withhopper.com, never in this chat.
3. Run `claim <email>` to wait. When it prints `Claimed`, carry on: the script uses the account key from then on, with the same history.

## In a voice agent's code

To add Hopper text-to-speech to an application rather than speak now, follow https://docs.withhopper.com/tts: `POST https://api.withhopper.com/v1/audio/speech` with `model: qwen3-tts`, a voice id, `input` up to 1,000 characters, and `stream: true` for the lowest time to first audio.

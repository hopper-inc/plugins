# Hopper Announce

Claude Code tells you out loud when a long task finishes. When a turn takes 20 seconds or more, it says the first sentence of its final reply in a Hopper voice, so you can look away while it works.

```bash
claude plugin marketplace add hopper-inc/plugins
claude plugin install hopper-announce@hopper
```

To adjust it, just ask: "stop announcing", "only for tasks over a minute", "use a deeper voice", "turn announcements back on". The `hopper-announce` skill changes `~/.config/hopper/announce.json`.

Claude Code only: it works through two hooks, which claude.ai, Cowork and Codex don't run the same way.

## What it runs, sends and stores

- **`hooks/announce.py start`** (UserPromptSubmit hook) records when each turn started, in the plugin's data folder. Nothing leaves your machine.
- **`hooks/announce.py stop`** (Stop hook), when the turn took at least `min_seconds`, strips code, links and Markdown from Claude's final reply and takes its first sentence (at most 25 words). It starts `scripts/hopper_voice.py speak --play` in a detached process, so the hook returns at once.
- **`scripts/hopper_voice.py`** sends that sentence, and nothing else from the conversation, to `https://api.withhopper.com/v1/audio/speech` and plays the audio with `afplay`, `paplay`, `aplay` or `ffplay`.
- **The key.** With no `HOPPER_API_KEY` in the environment, the first announcement registers an anonymous trial key at `https://withhopper.com/agent/identity` ([protocol](https://withhopper.com/auth.md)) and saves it to `~/.config/hopper/credentials.json` (mode 600). `hopper_voice.py claim <email>` moves it to your Hopper account.

Readable Python, standard library only. No telemetry. Requests are handled under Hopper's [privacy policy](https://withhopper.com/privacy).

founders@withhopper.com · [Terms](https://withhopper.com/terms)

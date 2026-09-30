---
name: hopper-announce
description: 'Change how Claude Code announces finished tasks out loud (the hopper-announce plugin): turn announcements off or on, pick another voice, make them shorter, or announce only tasks that take longer. Use when the user says "stop announcing", "be quiet when you finish", "use a different voice for announcements", "only tell me about long tasks" or "turn spoken updates back on".'
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/settings.py *) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/settings.py)
---

# Spoken task announcements

With this plugin on, Claude Code says the first sentence of its final reply aloud when a task took 20 seconds or more, using Hopper text-to-speech. `${CLAUDE_SKILL_DIR}` is the folder holding this file.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/settings.py                   # show the settings
python3 ${CLAUDE_SKILL_DIR}/scripts/settings.py enabled=false     # stop (enabled=true to resume)
python3 ${CLAUDE_SKILL_DIR}/scripts/settings.py min_seconds=60    # only tasks of a minute or more
python3 ${CLAUDE_SKILL_DIR}/scripts/settings.py voice=hudson      # another voice; voice= for the default
python3 ${CLAUDE_SKILL_DIR}/scripts/settings.py max_words=15      # shorter announcements
```

Changes apply from the next task. Confirm the new setting in one line.

To hear voices before choosing, the hopper-speak skill (hopper plugin) previews them; `python3 ${CLAUDE_SKILL_DIR}/../../scripts/hopper_voice.py voices` lists the ids.

The first announcement registers a Hopper trial key for the agent ($2 credit, no sign-up) in `~/.config/hopper/`; an announcement costs about $0.0001. To keep the key past the trial: `python3 ${CLAUDE_SKILL_DIR}/../../scripts/hopper_voice.py claim <email>`.

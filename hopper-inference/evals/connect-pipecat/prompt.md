---
description: After the benchmark, the user says go. Checks the switch follows the tested Pipecat page.
max_turns: 40
allowed_tools: [Read, Glob, Grep, Skill, Bash, Write, Edit]
---
You set up Hopper in this project earlier and benchmarked it: 71 ms first turn, 143 ms median on later turns, 90% prompt cache. The key is in .env. Go ahead: switch the LLM in bot.py to Hopper. Don't run the bot.

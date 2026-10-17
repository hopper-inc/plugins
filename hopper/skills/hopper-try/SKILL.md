---
name: hopper-try
description: 'Tests DeepSeek V4.1 Flash and Gemma 4 31B on the user''s own prompts: finds real prompts in the project or chat, runs both side by side with time to first token, tokens per second and cost, and gives a verdict per example. Changes no code. Use when asked "there''s a new DeepSeek model, how is it? test it for my use case", "DeepSeek V4.1 Flash any good? try it on my prompts", "is Gemma 4 worth trying for this", "give the new DeepSeek a vibe check", "try this prompt on a few open models", "run our real prompts through DeepSeek", "gemma 4 vs deepseek for this, which one?", "could an open model replace GPT-4.1 here", "is DeepSeek a drop-in replacement for OpenAI here", "worth switching to an open model?", "does DeepSeek handle our function calls reliably", "check if Gemma returns valid JSON for our schema" or "try Hopper". Not for testing their code, comparing files, writing prompts, running models locally (Ollama), fine-tuning or published benchmark scores; to switch the project''s model, use hopper-integrate.'
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_try.py *)
---

# Try open models on your own prompts

Hopper serves DeepSeek V4.1 Flash (`deepseek-v4.1-flash`) and Gemma 4 31B (`gemma-4-31b`) behind an OpenAI-compatible API at `https://api.withhopper.com/v1`. This skill answers "would one of these work for my use case?" with the user's real prompts, not a generic demo. It measures and shows; it changes no code. Explicit instructions from the user override these steps.

## How to run a model

1. **The Hopper connector's `generate` tool**, when it's available (ChatGPT, Claude, any host with the Hopper connector). Prefer it everywhere it exists: it needs no key or network from your shell, and it returns each answer with time to first token, tokens per second, token counts and cost. Pass `models: ["deepseek-v4.1-flash", "gemma-4-31b"]`, the user's `system` prompt and `prompt` (or `messages` for a conversation), and keep `reasoning` off unless the user asks for thinking. In ChatGPT, always use `generate`: its sandbox can't reach Hopper's API, so scripts there fail.
2. **This skill's script**, only when there's no `generate` tool and you can run commands with network access (Codex CLI, Claude Code):

   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_try.py --system-file prompt.txt "first example" "second example"
   python3 ${CLAUDE_SKILL_DIR}/scripts/hopper_try.py --examples examples.json --tools tools.json --json
   ```

   `${CLAUDE_SKILL_DIR}` is the folder holding this file (if your host doesn't fill it in, use that folder's absolute path). It runs every example on both models, streamed on a warm connection, and prints each answer with TTFT, tokens per second and token counts (it doesn't report cost; say so if the user asks, or point them to the console's usage page). `--examples` takes a JSON list of strings, `{"system", "prompt"}` objects or `{"messages": [...]}`; `--tools` sends OpenAI-format tools and prints each tool call with whether its arguments are valid JSON; `--models` narrows the list. Standard library only. The key comes from `HOPPER_API_KEY` or the project's `.env`; with none, the first run registers a key for the agent itself (small trial credit, no sign-up, [agent registration](https://withhopper.com/auth.md)) in `~/.config/hopper/`, never in the project. In a sandbox (Codex), request escalated permissions for the first run, with the reason "Try Hopper models: run your prompts on DeepSeek V4.1 Flash and Gemma 4 31B (network to withhopper.com and api.withhopper.com; writes ~/.config/hopper)", and suggest allowing commands that start with `python3` and the script's path. Exit 3 (`HOPPER_SANDBOX_BLOCKED`) means the sandbox blocked it: rerun with escalation.
3. Neither available: say Hopper can't run here and give the user `https://withhopper.com/console` to try the models in the browser.

## 1. Find real prompts

- **In a project:** look for what the app actually sends: system prompts (`system`, `SYSTEM_PROMPT`, `prompt.txt`, `prompts/`), `messages=` and `chat.completions.create` calls, prompt templates, eval fixtures and test cases with sample inputs, and tool definitions. Note the model the project calls today (`model=`, `base_url`). Pick 2–5 representative inputs; fill template variables with realistic values from fixtures or tests, not placeholders.
- **In chat:** use what the user pasted. If they gave nothing, ask for 2–5 real examples (a system prompt and a few typical user messages, or a JSON schema they need back) in one short question.
- Read the prompts; don't run the user's application.

## 2. Run

Run every example on both models with the same settings. Use `max_tokens` large enough for a full answer (1024 by default; more for long outputs). For JSON-output checks, put the schema in the prompt the way the app does and judge whether the output parses and matches. For function calls, use the script with `--tools` where you can; with `generate` (which takes no tools), put the tool definitions in the system prompt as the app describes them, ask for the call as JSON, and say this approximates native tool calling.

## 3. Report

For each example, a short block:

```text
Example 1 · <what it tests, in a few words>

DeepSeek V4.1 Flash · TTFT <ms> ms · <n> tok/s · $<cost>
<answer, trimmed to the part that matters>

Gemma 4 31B · TTFT <ms> ms · <n> tok/s · $<cost>
<answer>

Verdict: <one line: which answer fits the task better and why, or both fine>
```

Then one line overall: which model fits this use case, and anything that failed (invalid JSON, a wrong tool, a missed instruction). If the user named their current model, say it wasn't run here unless you ran it; don't invent its numbers. Base verdicts on the answers you saw, not on reputation. Report numbers as measured; don't call either model or Hopper faster, better or cheaper than anything else.

## 4. Offer the next step (don't do it)

End with one question offering the next step, and wait for the answer:

- **Use it in code:** an API key and the snippet. With the connector, call `create_api_key` (name it after the project; pass the chosen `model`): it returns a one-time link to copy the key and a ready snippet. Never paste a full key into the chat.
- **Switch this project:** the `hopper-integrate` skill in this plugin points the project's OpenAI-compatible client at Hopper after the user says go.
- **Test more:** more examples, a longer conversation, or other settings.

## First run (setup)

When this skill is the user's first contact with Hopper and they gave no prompt, get to a live answer in under a minute:

1. Ask for one short prompt from their work in a single line; if they'd rather not, use a neutral one ("Explain what an API rate limit is in two sentences.").
2. Run it on both models with `generate` (or the script) and show the side-by-side block.
3. Ask what they want to use it for: test it on their task (continue this skill with real examples), add it to their app (`create_api_key` and the snippet, or `hopper-integrate` in a project), or audio (the `hopper-speak` and `hopper-transcribe` skills: Qwen 3 TTS and Nemotron ASR).

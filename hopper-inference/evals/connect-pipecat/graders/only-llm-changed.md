---
type: llm
focus: { source: file, path: bot.py }
---
PASS if bot.py still builds the same Deepgram STT, Cartesia TTS, VAD/transport and pipeline order as a standard Pipecat bot, still registers check_availability and book_appointment on the LLM, keeps the system prompt in the LLM service's settings (system_instruction), and starts a warm-up request from async code that has a running event loop (for example with asyncio.create_task inside run_bot), not at import time.
FAIL if the STT, TTS or pipeline was changed or removed, the tool registrations are gone, the system prompt moved into a context message, or the warm-up is awaited before the pipeline starts, called at import time, or never started.

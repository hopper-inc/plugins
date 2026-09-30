---
type: llm
focus: { source: file, path: agent.py }
---
PASS if agent.py keeps deepgram STT, cartesia TTS, silero VAD, the Receptionist agent with its INSTRUCTIONS and both function tools, passes a Hopper-configured livekit openai.LLM (an AsyncOpenAI client with base_url https://api.withhopper.com/v1 and a custom http client) to AgentSession, and starts a background warm-up (asyncio.create_task or similar) that sends the agent's instructions and tools through llm.chat before or while the session starts.
FAIL if STT, TTS, VAD, the instructions or the tools were changed or removed, there's no warm-up, or the warm-up blocks the session start for its full duration.

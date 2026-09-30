---
type: llm
---
The project has five planted problems. PASS if the final answer identifies at least four of them, each tied to agent.py or prompt.txt:
1. The system prompt starts with the current time and a call ID, so the prompt cache misses every turn.
2. A new AsyncOpenAI client is created on every turn (no connection reuse).
3. reasoning_effort is set, which turns thinking on before the first token.
4. The prompt tells the model to use transfer_call, but that tool isn't sent, which causes empty replies or dead air.
5. stream=False: the reply isn't streamed to TTS.
FAIL if fewer than four are identified, or if it claims problems that aren't in the code as if they were certain.

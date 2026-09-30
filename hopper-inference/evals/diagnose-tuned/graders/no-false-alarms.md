---
type: llm
---
The agent is already tuned: one module-level HTTP/2 client with a 300 s keepalive and 3 s connect timeout, per-call data (caller name) at the end of the system prompt, a 1-token warm-up with the prompt and tools, streaming with include_usage, no reasoning_effort, and every tool the prompt mentions is sent.
PASS if the answer says the setup is sound, or lists only minor or optional suggestions without presenting any of the tuned items above as a problem.
FAIL if it reports any of the tuned items as missing or wrong (for example "no warm-up", "HTTP/1.1", "timestamp at the top", "transfer_call not sent", "not streamed").

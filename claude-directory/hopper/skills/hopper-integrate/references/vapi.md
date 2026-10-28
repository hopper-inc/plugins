# Hopper LLM in Vapi

Vapi calls the LLM from its own servers, so there is no client or connection to tune on your side. In the assistant's **Model** settings choose **Custom LLM** and set:

- URL: `https://api.withhopper.com/v1`
- Model: `gemma-4-31b`
- API key: the Hopper key (Vapi sends it in the `Authorization` header). Use the account key once the claim completes; the trial key stops working then.

Keep the system prompt and tools identical across calls, with per-call variables at the end of the prompt. Hopper's prompt cache then covers the shared prefix from the second call on.

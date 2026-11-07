# Model runtime integration map

No model server, model weights, or inference provider is started by this repository's local setup. AI-1 through AI-7 are local deterministic/statistical components and do not call an LLM.

Ollama, llama.cpp, vLLM, and LocalAI are candidates for later, separate changes. Before adding a runtime, verify its license and image digest, hardware requirements, network exposure, data handling, and whether it can remain local and cost-free. Do not commit model weights, API keys, or customer telemetry.

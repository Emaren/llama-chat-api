# app/agent_models.py
# ------------------------------------------------------------------
# Map UI-agent names → Ollama model tags
# ------------------------------------------------------------------

model_routes: dict[str, str] = {
    "LlamaAgent38BIQ2KM": "llama3:8b-instruct-q2_K",
    "LlamaAgent38BIQ3KM": "llama3:8b-instruct-q3_K_M",   # Q3, with memory
    "LlamaAgent38BIQ4KM": "llama3:8b-instruct-q4_K_M",   # Q4, with memory
    "LlamaAgent42":       "llama3:8b-instruct-q4_K_M",               # with memory
    "WoloDaemon":         "llama3:8b-instruct-q4_K_M",               # with memory
    "LlamaBear":          "llama3:8b-instruct-q4_K",               # **no memory layer**
    "Agent4o":            "openai:gpt-4o",  # ✅ ChatGPT-4o Raw API Mode **no memory layer**
    "Agent4oM":           "openai:gpt-4o",  # ✅ New memory-persistent OpenAI agent
}

# app/agent_models.py
# ------------------------------------------------------------------
# Map UI-agent names -> Ollama/OpenAI model tags
# ------------------------------------------------------------------

model_routes: dict[str, str] = {
    "Agent4o":            "openai:gpt-4o",      # ChatGPT-4o Raw API Mode (no memory layer)
    "Agent4oM":           "openai:gpt-4o",      # New memory-persistent OpenAI agent
    "LlamaAgent38BIQ2KM": "llama3:8b-instruct-q2_K",
    "LlamaAgent38BIQ3KM": "llama3:8b-instruct-q3_K_M",  # Q3, with memory
    "LlamaAgent38BIQ4KM": "llama3:8b-instruct-q4_K_M",  # Q4, with memory
    "LlamaAgent42":       "llama3:8b-instruct-q4_K_M",  # with memory
    "WoloDaemon":         "llama3:8b-instruct-q4_K_M",  # with memory
    "LlamaBear":          "llama3:8b-instruct-q4_K",    # no memory layer
    "Agent4.1M":          "openai:gpt-4.1",             # New memory-persistent OpenAI agent
    "Agent4.1Scribe":     "openai:gpt-4.1",             # Scribe lane
    "Agent4.1Grimer":     "openai:gpt-4.1",             # Grimer lane
    "Agent4.1Guy":        "openai:gpt-4.1",             # Guy of Moxica lane
    "Agent4.1Doc":        "openai:gpt-4.1",             # Doc lane
    "Agent4.1Leonidas":   "openai:gpt-4.1",             # Leonidas lane
    "Agent4.1Don":        "openai:gpt-4.1",             # Don lane
    "Agent4.1Han":        "openai:gpt-4.1",             # Han lane
    "Agent4.1Bill":       "openai:gpt-4.1",             # Bill lane
    "Agent4.1Sean":       "openai:gpt-4.1",             # Sean lane
    "Agent4.1Joe":        "openai:gpt-4.1",             # Joe lane
    "Agent4oMP":          "openai:gpt-4o",              # ChatGPT-4o prompt agent with local memory
}

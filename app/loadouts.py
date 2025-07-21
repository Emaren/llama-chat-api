# app/loadouts.py

LOADOUTS = {
    "ParseKnight": {
        "persona": "ParseKnight",
        "model": "LlamaAgent42",
        "tools": ["parse_replay.py", "watch_replays.py", "game_stats.sql"],
        "description": "Used for AoE2 replay parsing and data ingestion tasks."
    },
    "Agent4oM": {
        "persona": "Agent4oM",
        "model": "Agent4oM",
        "tools": ["llama_context_snapshot.txt", "loadouts.py", "llama-chat-api", "llama-chat-app"],
        "description": "Tony’s immortal right hand for dev, ops, and memory continuity."
    },
    "Agent4oMP": {
        "persona": "Agent4oMP",           # ↩︎ any prompt/persona tag you want
        "model":   "openai:gpt-4o",  # ↩︎ **openai:** prefix is the key!
        "tools":   [],                    # or tools the agent may call
        "description": "Primary OpenAI-powered dev assistant",
    },
}

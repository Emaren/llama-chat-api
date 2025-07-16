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
    # Add more here…
}

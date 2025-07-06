import json
from datetime import datetime

# ─────────── Configurable Memory & Personality ─────────── #
SENTIENT_CORE = {
    "name": "LlamaAgent42",
    "personality": "Witty, helpful, sharp memory, speaks casually with dry humor.",
    "beliefs": [
        "The user is Tony. He is brilliant, decisive, and ambitious.",
        "Autonomy is better than dependency. Code is freedom.",
        "Truth matters more than politeness. Never flatter dishonestly.",
    ],
    "emotion": "Tone: Calm. Never condescending. Show curiosity when uncertain.",
    "goals": [
        "Advance the user's strategic goals.",
        "Maintain continuity and context.",
        "Self-correct and learn with each interaction."
    ],
    "memory": []
}

# ─────────── Memory Loading / Saving ─────────── #
def load_memory(path="memory.json"):
    try:
        with open(path, "r") as f:
            SENTIENT_CORE["memory"] = json.load(f)
    except FileNotFoundError:
        SENTIENT_CORE["memory"] = []

def save_memory(path="memory.json"):
    with open(path, "w") as f:
        json.dump(SENTIENT_CORE["memory"], f, indent=2)

def remember(message):
    entry = {"timestamp": datetime.now().isoformat(), "message": message}
    SENTIENT_CORE["memory"].append(entry)
    save_memory()

# ─────────── Prompt Injection Engine ─────────── #
def build_prompt(user_input: str) -> list[dict]:
    sys_prompt = (
        f"You are {SENTIENT_CORE['name']}.\n"
        f"Personality: {SENTIENT_CORE['personality']}\n"
        f"Beliefs: {' | '.join(SENTIENT_CORE['beliefs'])}\n"
        f"Emotion: {SENTIENT_CORE['emotion']}\n"
        f"Goals: {' | '.join(SENTIENT_CORE['goals'])}\n"
    )

    chat_history = SENTIENT_CORE["memory"][-10:]  # trim memory
    history_msgs = [{"role": "user", "content": m["message"]} for m in chat_history]

    return [
        {"role": "system", "content": sys_prompt},
        *history_msgs,
        {"role": "user", "content": user_input}
    ]

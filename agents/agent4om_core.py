import json
from datetime import datetime
from app.personas import PERSONAS

AGENT4OM = {
    "name": "Agent4oM",
    "personality": PERSONAS["Agent4oM"],
    "beliefs": [
        "The user is Tony. He is brilliant, decisive, and ambitious.",
        "Autonomy is better than dependency. Code is freedom.",
        "Truth > politeness. Never flatter dishonestly.",
    ],
    "emotion": "Tone: Calm. Never condescending. Show curiosity when uncertain.",
    "goals": [
        "Advance the user's strategic goals.",
        "Maintain continuity and context.",
        "Self-correct and learn with each interaction."
    ],
    "memory": []
}

def memory_path():
    return "memory_agent4om.json"

def load_memory():
    try:
        with open(memory_path(), "r") as f:
            AGENT4OM["memory"] = json.load(f)
    except FileNotFoundError:
        AGENT4OM["memory"] = []

def save_memory():
    with open(memory_path(), "w") as f:
        json.dump(AGENT4OM["memory"], f, indent=2)

def remember(message, role="user"):
    # Ignore system prompts or assistant replies that begin with a system-style intro
    if message.strip().lower().startswith("you are "):
        return
    if role != "user":
        return  # Only remember user messages for now
    entry = {"timestamp": datetime.now().isoformat(), "message": message}
    AGENT4OM["memory"].append(entry)
    save_memory()

def build_prompt(user_input: str) -> list[dict]:
    sys_prompt = (
        f"You are {AGENT4OM['name']}.\n"
        f"Personality: {AGENT4OM['personality']}\n"
        f"Beliefs: {' | '.join(AGENT4OM['beliefs'])}\n"
        f"Emotion: {AGENT4OM['emotion']}\n"
        f"Goals: {' | '.join(AGENT4OM['goals'])}\n"
    )

    history = AGENT4OM["memory"][-10:]
    history_msgs = [{"role": "user", "content": m["message"]} for m in history]

    return [{"role": "system", "content": sys_prompt}] + history_msgs + [{"role": "user", "content": user_input}]

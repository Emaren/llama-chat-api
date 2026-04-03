from app.memory import load_memory, trim_history

def handle_chat(agent_name, user_input):
    # /send owns persistence; this builds the in-memory transcript once.
    history = load_memory(agent_name)
    trim_history(history)
    history.append({"role": "user", "content": user_input})
    return history

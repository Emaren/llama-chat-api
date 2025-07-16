from app.memory import load_memory, save_memory, trim_history

def handle_chat(agent_name, user_input):
    # 🧠 Always support memory for all agents, including prompt-based ones
    history = load_memory(agent_name)
    trim_history(history)
    history.append({"role": "user", "content": user_input})
    save_memory(agent_name, history)
    return history

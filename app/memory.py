import os
import json

MEMORY_DIR = os.path.join(os.path.dirname(__file__), '..', 'memory')
os.makedirs(MEMORY_DIR, exist_ok=True)

def memory_path(agent_name):
    return os.path.join(MEMORY_DIR, f"{agent_name}.json")

def load_memory(agent_name):
    path = memory_path(agent_name)
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        return json.load(f)

def save_memory(agent_name, history):
    path = memory_path(agent_name)
    with open(path, 'w') as f:
        json.dump(history, f)

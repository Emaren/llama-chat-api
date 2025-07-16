from agents.agent4om_core import AGENT4OM, build_prompt as agent4om_prompt, remember as agent4om_remember, load_memory as agent4om_load

AGENT_REGISTRY = {
    "Agent4oM": {
        "brain": AGENT4OM,
        "build_prompt": agent4om_prompt,
        "remember": agent4om_remember,
        "load_memory": agent4om_load,
    }
}

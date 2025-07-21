from agents.agent4om_core import AGENT4OM, build_prompt as agent4om_prompt, remember as agent4om_remember, load_memory as agent4om_load
from agents.agent4omp_core import Agent4oMP

AGENT_REGISTRY = {
    "Agent4oM": {
        "brain": AGENT4OM,
        "build_prompt": agent4om_prompt,
        "remember": agent4om_remember,
        "load_memory": agent4om_load,
    },
    "Agent4oMP": {
        "brain": Agent4oMP,
        # if you have wrapper funcs for building prompts/memory, plug them in here
    }
}

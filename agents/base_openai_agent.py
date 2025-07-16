# agents/base_openai_agent.py
class OpenAIAgent:
    prompt_id = None
    prompt_version = None

    def __init__(self, agent: str):
        self.agent = agent

    def __call__(self):
        if self.prompt_id:
            return {
                "model": self.model,
                "prompt": {
                    "id": self.prompt_id,
                    "version": self.prompt_version or "1"
                }
            }
        else:
            return {
                "model": self.model,
                "system_prompt": self.system_prompt
            }

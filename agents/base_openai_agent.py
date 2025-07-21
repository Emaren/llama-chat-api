# agents/base_openai_agent.py

from typing import AsyncIterator, Optional
from langchain_community.chat_models import ChatOpenAI
from openai import AsyncOpenAI


class _PromptManagedLLM:
    """
    Adapter for the OpenAI Prompt-Management `/responses` endpoint.
    • __call__() does a single non-streaming call and returns the full text.
    • astream() is still here if you ever want to stream chunk-by-chunk.
    """
    def __init__(self, prompt_id: str, prompt_version: Optional[str] = None):
        self._prompt: dict = {"id": prompt_id}
        if prompt_version:
            self._prompt["version"] = prompt_version
        self._client = AsyncOpenAI()

    async def __call__(self, user_text: str) -> str:
        """
        Non-streaming: pull back the completed text in one go.
        """
        resp = await self._client.responses.create(
            prompt=self._prompt,
            input=user_text,
            stream=False,
        )
        # resp.output is a list; each item has .content which is a list of
        # {text, ...}. We grab the first chunk’s text.
        return resp.output[0].content[0].text

    async def astream(self, user_text: str) -> AsyncIterator[str]:
        """
        If you really want streaming, you can still call stream=True
        and yield each `event.output` chunk.
        """
        stream = await self._client.responses.create(
            prompt=self._prompt,
            input=user_text,
            stream=True,
        )
        async for event in stream:
            piece = getattr(event, "output", None)
            if piece:
                yield piece


class OpenAIAgent:
    """
    Base agent: subclasses that set `prompt_id` will go
    through Prompt-Management; others use ChatOpenAI.
    """

    # override in subclasses:
    prompt_id:      Optional[str] = None
    prompt_version: Optional[str] = None
    model:          str            = "gpt-4o"

    def __init__(self, **kwargs):
        self.model = getattr(self, "model", self.model)

        if self.prompt_id:
            version = getattr(self, "prompt_version", None)
            self.llm = _PromptManagedLLM(self.prompt_id, version)
            print(f"[Agent Init] Prompt-Mgmt id={self.prompt_id} v={version or '1'}")
        else:
            self.llm = ChatOpenAI(
                model_name=self.model,
                temperature=0.7,
                streaming=True,
                **kwargs,
            )
            print(f"[Agent Init] ChatOpenAI model={self.model}")

    async def run(self, user_input: str) -> str:
        """
        Single entry point: dispatch to prompt-managed or vanilla path.
        """
        if self.prompt_id:
            return await self.llm(user_input)       # non-streaming full-text
        else:
            return await self.llm.run(user_input)  # LangChain streaming path

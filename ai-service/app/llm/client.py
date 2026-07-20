from dataclasses import dataclass


@dataclass
class LLMClient:
    model: str = "gpt-5.4-mini"

    async def generate(self, prompt: str) -> str:
        return prompt
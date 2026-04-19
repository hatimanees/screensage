from .base import LLMProvider
from .gemini import GeminiLLM


def get_llm_provider(name: str, config: dict) -> LLMProvider:
    if name == "gemini":
        return GeminiLLM(
            api_key=config["gemini"]["api_key"],
            model=config["gemini"].get("model", "gemini-2.0-flash"),
        )
    raise ValueError(f"Unknown LLM provider: {name}")

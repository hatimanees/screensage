from .base import STTProvider
from .deepgram import DeepgramSTT


def get_stt_provider(name: str, config: dict) -> STTProvider:
    if name == "deepgram":
        return DeepgramSTT(api_key=config["deepgram"]["api_key"])
    raise ValueError(f"Unknown STT provider: {name}")

from abc import ABC, abstractmethod


class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        pass

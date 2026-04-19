from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def analyze(self, image_path: str, query: str, context: str) -> str:
        pass

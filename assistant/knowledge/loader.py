import json
from pathlib import Path

_KNOWLEDGE_PATH = Path(__file__).parent / "data.json"


def load_knowledge() -> dict:
    with open(_KNOWLEDGE_PATH, "r") as f:
        return json.load(f)

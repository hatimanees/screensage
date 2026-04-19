import json
from datetime import datetime
from pathlib import Path

SESSIONS_DIR = Path(__file__).parent.parent.parent / "sessions"


def list_sessions(limit: int = 10) -> list[dict]:
    """Return up to `limit` session dicts, newest first. Each dict has 'path' + session data."""
    if not SESSIONS_DIR.exists():
        return []
    files = sorted(SESSIONS_DIR.glob("session_*.json"), reverse=True)
    out = []
    for f in files[:limit]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            out.append({"path": f, **data})
        except Exception:
            pass
    return out


def load_history(path: Path) -> list[tuple[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [(t["query"], t["response"]) for t in data.get("turns", [])]


class SessionWriter:
    """Writes / appends turns to a JSON session file."""

    def __init__(self, existing_path: Path | None = None):
        SESSIONS_DIR.mkdir(exist_ok=True)
        if existing_path:
            self._path = existing_path
            self._data = json.loads(existing_path.read_text(encoding="utf-8"))
            self._data.setdefault("resumed_at", []).append(
                datetime.now().isoformat(timespec="seconds")
            )
        else:
            ts = datetime.now().strftime("session_%Y%m%d_%H%M%S")
            self._path = SESSIONS_DIR / f"{ts}.json"
            self._data = {
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "turns": [],
            }
        self._flush()

    def append(self, query: str, response: str) -> None:
        self._data["turns"].append({
            "query":     query,
            "response":  response,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })
        self._flush()

    def _flush(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @property
    def path(self) -> Path:
        return self._path

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import typer
import yaml
from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent.parent / ".env"

app = typer.Typer(add_completion=False)


def _prompt_and_save_missing_keys(env_path: Path, required_keys: list[str]) -> None:
    """For any required key not in the environment, prompt the user and save to .env."""
    missing = [k for k in required_keys if not os.getenv(k)]
    if not missing:
        return

    print("\n-- First-time setup --")
    print("Some API keys are missing. Enter them below and they will be saved to .env.\n")

    # Read existing .env lines so we can append without overwriting
    existing_lines: list[str] = []
    if env_path.exists():
        existing_lines = env_path.read_text().splitlines()

    new_lines: list[str] = []
    for key in missing:
        value = input(f"  {key}: ").strip()
        os.environ[key] = value          # available for the rest of this process
        new_lines.append(f"{key}={value}")

    with open(env_path, "a") as f:
        if existing_lines and existing_lines[-1] != "":
            f.write("\n")
        f.write("\n".join(new_lines) + "\n")

    print(f"\nKeys saved to {env_path}. Starting ScreenSage...\n")


_OPTIONAL_KEYS = {"SERPER_API_KEY"}


def _load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        raw = yaml.safe_load(f)

    # Collect every ${VAR} referenced in config; optional keys are not prompted
    all_keys: list[str] = []
    for section, values in raw.items():
        if isinstance(values, dict):
            for v in values.values():
                if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                    all_keys.append(v[2:-1])

    required_keys = [k for k in all_keys if k not in _OPTIONAL_KEYS]

    load_dotenv(dotenv_path=ENV_PATH)
    _prompt_and_save_missing_keys(ENV_PATH, required_keys)

    if not os.getenv("SERPER_API_KEY"):
        print("  Note: SERPER_API_KEY not set — web search disabled.")
        print("  Get a free key at serper.dev (2,500 searches/month) and add it to .env\n")

    def _expand(val):
        if isinstance(val, str) and val.startswith("${") and val.endswith("}"):
            key = val[2:-1]
            if key in _OPTIONAL_KEYS:
                return os.environ.get(key, "")
            return os.environ[key]   # guaranteed present after prompt above
        return val

    for section, values in raw.items():
        if isinstance(values, dict):
            for k, v in values.items():
                raw[section][k] = _expand(v)

    return raw


def _pick_session():
    """Terminal session picker.

    Returns (initial_history, existing_session_path | None).
    The SessionWriter is created lazily by Agent on first actual turn,
    so no empty session files accumulate on disk.
    """
    from core.session import list_sessions, load_history

    # Only show sessions that have at least one recorded turn
    all_sessions = list_sessions(limit=20)
    sessions = [s for s in all_sessions if len(s.get("turns", [])) > 0]

    if not sessions:
        return [], None

    print("\n-- Session History --\n")
    for i, s in enumerate(sessions, 1):
        dt_raw = s.get("started_at", "")
        try:
            dt = datetime.fromisoformat(dt_raw).strftime("%b %d  %H:%M")
        except Exception:
            dt = dt_raw[:16]
        turns   = len(s.get("turns", []))
        turns_  = s.get("turns", [])
        preview = ""
        if turns_:
            q = turns_[0].get("query", "")
            preview = q[:60].replace("\n", " ")
            if len(q) > 60:
                preview += "…"
        resumed = "  (resumed)" if s.get("resumed_at") else ""
        print(f"  [{i}]  {dt}  ({turns} turn{'s' if turns != 1 else ''})  \"{preview}\"{resumed}")

    print(f"\n  [N]  Start a new session\n")

    choice = input("Resume [N]: ").strip().upper()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(sessions):
            chosen   = sessions[idx]
            history  = load_history(chosen["path"])
            print(f"\nResuming session with {len(history)} prior turn(s). Starting ScreenSage...\n")
            return history, chosen["path"]

    print("\nStarting new session...\n")
    return [], None


@app.command()
def guide():
    """Capture your screen and voice, then get step-by-step guidance."""
    from PyQt6.QtWidgets import QApplication

    config = _load_config()
    history, session_path = _pick_session()

    from providers.stt.factory import get_stt_provider
    from providers.llm.factory import get_llm_provider
    from ui.recording_bar import RecordingBar
    from core.agent import Agent

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("ScreenSage")
    qt_app.setQuitOnLastWindowClosed(False)   # overlay closing doesn't quit

    from core.tool_executor import ToolExecutor

    stt           = get_stt_provider(config["stt"], config)
    llm           = get_llm_provider(config["llm"], config)
    tool_executor = ToolExecutor(serper_api_key=config["serper"]["api_key"])

    bar = RecordingBar()
    bar.show()

    agent = Agent(stt, llm, tool_executor, bar,   # noqa: F841 — must stay alive
                  history=history, session_path=session_path)

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    app()

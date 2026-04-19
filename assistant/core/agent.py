import os

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from capture.audio import AudioRecorder
from capture.screen import capture_screen
from core.session import SessionWriter
from pathlib import Path


# ── Background worker ────────────────────────────────────────────────────────

class _Worker(QThread):
    result_ready   = pyqtSignal(str, str)   # (response_text, transcript)
    error_occurred = pyqtSignal(str)

    def __init__(self, stt, llm, tool_executor, history, audio_path: str, screenshot_path: str):
        super().__init__()
        self._stt             = stt
        self._llm             = llm
        self._tool_executor   = tool_executor
        self._history         = history
        self._audio_path      = audio_path
        self._screenshot_path = screenshot_path

    def run(self):
        try:
            transcript = self._stt.transcribe(self._audio_path)
            print(f"\n[transcript] {transcript}")
            print(f"[history] {len(self._history)} prior turn(s)")
            response   = self._llm.analyze_with_tools(
                self._screenshot_path, transcript, self._tool_executor, self._history
            )
            self.result_ready.emit(response, transcript)
        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            for p in (self._audio_path, self._screenshot_path):
                try:
                    os.remove(p)
                except OSError:
                    pass


# ── Agent ────────────────────────────────────────────────────────────────────

class Agent(QObject):
    def __init__(self, stt, llm, tool_executor, bar,
                 history: list[tuple[str, str]] | None = None,
                 session_path: Path | None = None):
        super().__init__()
        self._stt            = stt
        self._llm            = llm
        self._tool_executor  = tool_executor
        self._bar            = bar
        self._recorder       = AudioRecorder()
        self._worker: _Worker | None = None
        self._overlay        = None   # keep reference alive
        self._history: list[tuple[str, str]] = list(history or [])
        # Writer is created on first turn: resuming opens existing file, new session creates one
        self._session: SessionWriter | None = (
            SessionWriter(existing_path=session_path) if session_path else None
        )

        bar.start_clicked.connect(self._on_start)
        bar.stop_clicked.connect(self._on_stop)
        bar.delete_clicked.connect(self._on_delete)

    def _on_start(self):
        self._recorder.start()

    def _on_stop(self):
        audio_path = self._recorder.stop()

        # Hide bar so it doesn't appear in the screenshot,
        # then capture after a short delay for the OS to redraw.
        self._bar.hide()
        QTimer.singleShot(180, lambda: self._do_screenshot(audio_path))

    def _do_screenshot(self, audio_path: str):
        screenshot_path = capture_screen()
        self._bar.show()                    # bar comes back in PROCESSING state

        self._worker = _Worker(self._stt, self._llm, self._tool_executor, list(self._history), audio_path, screenshot_path)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

    def _on_delete(self):
        self._recorder.discard()

    def _on_result(self, text: str, transcript: str):
        self._history.append((transcript, text))
        if self._session is None:
            self._session = SessionWriter()   # create on first real turn
        self._session.append(transcript, text)
        self._bar.set_idle()
        from ui.overlay import ResultOverlay
        self._overlay = ResultOverlay(text, transcript, self._bar)
        # overlay positions and shows itself via QTimer.singleShot(0)

    def _on_error(self, error: str):
        print(f"[ScreenSage] error: {error}")
        self._bar.set_idle()

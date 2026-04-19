import tempfile
import threading
import wave
import numpy as np
import sounddevice as sd


SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"


class AudioRecorder:
    def __init__(self):
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._recording = False

    def start(self):
        self._frames = []
        self._recording = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata: np.ndarray, frames: int, time, status):
        if self._recording:
            with self._lock:
                self._frames.append(indata.copy())

    def stop(self) -> str:
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        return self._save()

    def discard(self):
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._frames = []

    def _save(self) -> str:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()

        with self._lock:
            frames = self._frames[:]

        if not frames:
            # Write a minimal valid WAV (silence) so downstream doesn't crash
            audio_data = np.zeros((SAMPLE_RATE,), dtype=np.int16)
        else:
            audio_data = np.concatenate(frames, axis=0).flatten()

        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())

        return tmp.name

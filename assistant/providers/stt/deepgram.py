from deepgram import DeepgramClient
from .base import STTProvider


class DeepgramSTT(STTProvider):
    def __init__(self, api_key: str):
        self._client = DeepgramClient(api_key=api_key)

    def transcribe(self, audio_path: str) -> str:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        response = self._client.listen.v1.media.transcribe_file(
            request=audio_bytes,
            model="nova-2",
            smart_format=True,
            language="en",
        )
        transcript = response.results.channels[0].alternatives[0].transcript
        return transcript.strip()

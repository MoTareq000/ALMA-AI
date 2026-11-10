from typing import Optional
from .interface import BaseTTSClient


class FakeTTSClient(BaseTTSClient):
    """Deterministic offline mock TTS client returning minimal valid MP3 frame bytes."""

    def __init__(self):
        # Minimal valid MPEG-1 Audio Layer III (MP3) frame sequence
        frame = b"\xff\xfb\x90\x00" + (b"\x00" * 414)
        self._dummy_mp3 = frame * 4

    def synthesize(
        self,
        text: str,
        voice_name: Optional[str] = None,
        speaking_rate: Optional[float] = None,
    ) -> bytes:
        return self._dummy_mp3


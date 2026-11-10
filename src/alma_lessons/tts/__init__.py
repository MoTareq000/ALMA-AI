from typing import Optional
from .interface import BaseTTSClient
from .audio_cache import AudioCacheManager, audio_cache
from .fake_tts import FakeTTSClient
from .google_tts import GoogleCloudTTSClient
from ..config import config


def get_tts_client(provider: Optional[str] = None) -> BaseTTSClient:
    """Factory returning configured TTS client (defaults to Google Cloud TTS or FakeTTS)."""
    selected = (provider or "google").lower()
    if selected == "fake":
        return FakeTTSClient()
    return GoogleCloudTTSClient()


__all__ = [
    "BaseTTSClient",
    "AudioCacheManager",
    "audio_cache",
    "FakeTTSClient",
    "GoogleCloudTTSClient",
    "get_tts_client",
]


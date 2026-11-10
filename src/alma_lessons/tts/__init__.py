from typing import Optional
from .interface import BaseTTSClient
from .audio_cache import AudioCacheManager, audio_cache
from .fake_tts import FakeTTSClient
from .google_tts import GoogleCloudTTSClient
from .gtts_client import GTTSClient
from ..config import config


def get_tts_client(provider: Optional[str] = None) -> BaseTTSClient:
    """Factory returning configured TTS client.
    Supports 'gtts' (free/instant), 'google_cloud' (Journey/Neural2), 'auto', or 'fake'.
    """
    selected = (provider or config.tts_provider or "auto").lower()
    if selected == "fake":
        return FakeTTSClient()
    if selected == "gtts":
        return GTTSClient()
    if selected in ("google", "google_cloud", "journey", "neural2"):
        return GoogleCloudTTSClient(allow_fallback=False)
    # Default 'auto': attempts Google Cloud TTS, seamlessly falls back to gTTS
    return GoogleCloudTTSClient(allow_fallback=True)


__all__ = [
    "BaseTTSClient",
    "AudioCacheManager",
    "audio_cache",
    "FakeTTSClient",
    "GoogleCloudTTSClient",
    "GTTSClient",
    "get_tts_client",
]

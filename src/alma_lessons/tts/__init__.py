from typing import Optional
from .interface import BaseTTSClient
from .audio_cache import AudioCacheManager, audio_cache
from .fake_tts import FakeTTSClient
from .google_tts import GoogleCloudTTSClient
from .gtts_client import GTTSClient
from .edge_tts_client import EdgeTTSClient
from .kokoro_tts import KokoroTTSClient
from .personalizer import build_personalized_script
from ..config import config


def get_tts_client(provider: Optional[str] = None) -> BaseTTSClient:
    """Factory returning configured TTS client.
    Supports:
        - 'kokoro': Kokoro-82M (Hugging Face / fal-ai)
        - 'edge' / 'neural': Microsoft Edge Neural HD voices (Free, zero setup)
        - 'gtts': Basic Google TTS (Free, standard voice)
        - 'google_cloud' / 'journey': Google Cloud Journey/Neural2 (Requires GCP Service Account)
        - 'fake': Deterministic test audio (zero cost, test suites)
    """
    selected = (provider or config.tts_provider or "kokoro").lower()
    if selected == "fake":
        return FakeTTSClient()
    if selected in ("kokoro", "hexgrad/kokoro-82m"):
        return KokoroTTSClient()
    if selected in ("edge", "edge_tts", "neural", "free_neural", "auto"):
        return EdgeTTSClient()
    if selected == "gtts":
        return GTTSClient()
    if selected in ("google", "google_cloud", "journey", "neural2"):
        return GoogleCloudTTSClient(allow_fallback=True)
    return KokoroTTSClient()


__all__ = [
    "BaseTTSClient",
    "AudioCacheManager",
    "audio_cache",
    "FakeTTSClient",
    "GoogleCloudTTSClient",
    "GTTSClient",
    "EdgeTTSClient",
    "KokoroTTSClient",
    "build_personalized_script",
    "get_tts_client",
]

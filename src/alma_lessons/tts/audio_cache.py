import hashlib
from pathlib import Path
from typing import Optional
from ..config import config


class AudioCacheManager:
    """Manages disk-based caching of synthesized audio files."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = Path(cache_dir or config.audio_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_cache_key(text: str, voice_name: str, speaking_rate: float = 1.0) -> str:
        """Generate deterministic sha256 hash for speech content and acoustic params."""
        clean_text = text.strip()
        data = f"{voice_name}::{speaking_rate:.2f}::{clean_text}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def get_audio_path(self, cache_key: str) -> Optional[Path]:
        """Return Path to cached audio file if it exists, else None."""
        target = self.cache_dir / f"{cache_key}.mp3"
        return target if target.is_file() else None

    def has_audio(self, cache_key: str) -> bool:
        """Check if audio exists in cache."""
        return (self.cache_dir / f"{cache_key}.mp3").is_file()

    def save_audio(self, cache_key: str, audio_bytes: bytes) -> Path:
        """Save synthesized audio bytes to cache file."""
        target = self.cache_dir / f"{cache_key}.mp3"
        target.write_bytes(audio_bytes)
        return target


audio_cache = AudioCacheManager()


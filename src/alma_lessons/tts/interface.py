from abc import ABC, abstractmethod
from typing import Optional


class BaseTTSClient(ABC):
    """Abstract client interface for Text-to-Speech synthesis."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_name: Optional[str] = None,
        speaking_rate: Optional[float] = None,
    ) -> bytes:
        """Synthesize text into MP3 audio bytes."""
        pass


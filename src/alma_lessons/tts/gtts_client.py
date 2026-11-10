import io
from typing import Optional
from gtts import gTTS
import structlog
from .interface import BaseTTSClient

logger = structlog.get_logger(__name__)


class GTTSClient(BaseTTSClient):
    """Zero-configuration Google Text-to-Speech client using gTTS.
    Produces real natural speech without requiring GCP credentials or API keys.
    """

    def synthesize(
        self,
        text: str,
        voice_name: Optional[str] = None,
        speaking_rate: Optional[float] = None,
    ) -> bytes:
        logger.info("gtts_synthesis_requested", chars=len(text))
        fp = io.BytesIO()
        tld = "com"
        if voice_name:
            v_lower = voice_name.lower()
            if "uk" in v_lower or "british" in v_lower:
                tld = "co.uk"
            elif "au" in v_lower or "australian" in v_lower:
                tld = "com.au"
            elif "ca" in v_lower:
                tld = "ca"

        tts = gTTS(text=text.strip(), lang="en", tld=tld, slow=False)
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()


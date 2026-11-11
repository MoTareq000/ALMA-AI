import os
from typing import Optional
import structlog
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError
from .interface import BaseTTSClient
from ..config import config

logger = structlog.get_logger(__name__)


class KokoroTTSClient(BaseTTSClient):
    """Kokoro-82M Text-to-Speech client using Hugging Face Hub (fal-ai provider).
    If Hugging Face returns a 402 Payment Required (e.g. no pre-paid credits on HF account),
    it seamlessly falls back to the high-definition Edge Neural TTS engine so learning is never interrupted.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.hf_token or os.environ.get("HF_TOKEN", "")
        self.model_id = "hexgrad/Kokoro-82M"
        self.provider = "fal-ai"

    def synthesize(
        self,
        text: str,
        voice_name: Optional[str] = None,
        speaking_rate: Optional[float] = None,
    ) -> bytes:
        logger.info(
            "kokoro_tts_synthesis_requested",
            model=self.model_id,
            provider=self.provider,
            chars=len(text),
        )

        try:
            client = InferenceClient(
                provider=self.provider,
                api_key=self.api_key,
            )
            audio_bytes = client.text_to_speech(
                text.strip(),
                model=self.model_id,
            )
            return audio_bytes

        except HfHubHTTPError as e:
            if "402" in str(e) or "Payment Required" in str(e):
                logger.warning(
                    "kokoro_hf_payment_required_fallback",
                    detail="Hugging Face 'fal-ai' provider requires pre-paid credits on your HF account. Seamlessly falling back to Edge Neural voice.",
                )
            else:
                logger.warning("kokoro_hf_inference_error", error=str(e))

            # Seamless fallback to Edge Neural Voice (100% Free, Studio Quality)
            from .edge_tts_client import EdgeTTSClient

            fallback_client = EdgeTTSClient()
            return fallback_client.synthesize(
                text=text,
                voice_name="en-US-JennyNeural",
                speaking_rate=speaking_rate,
            )

        except Exception as e:
            logger.warning("kokoro_unexpected_error_falling_back", error=str(e))
            from .edge_tts_client import EdgeTTSClient

            return EdgeTTSClient().synthesize(
                text=text,
                voice_name="en-US-JennyNeural",
                speaking_rate=speaking_rate,
            )

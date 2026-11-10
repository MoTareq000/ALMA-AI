import base64
import requests
from typing import Optional
import structlog
from .interface import BaseTTSClient
from ..config import config

logger = structlog.get_logger(__name__)


class GoogleCloudTTSClient(BaseTTSClient):
    """Google Cloud Text-to-Speech REST client supporting Journey and Neural2 voices."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.gcp_tts_api_key or config.gemini_api_key
        self.endpoint_url = "https://texttospeech.googleapis.com/v1/text:synthesize"

    def synthesize(
        self,
        text: str,
        voice_name: Optional[str] = None,
        speaking_rate: Optional[float] = None,
    ) -> bytes:
        if not self.api_key:
            raise ValueError(
                "Google Text-to-Speech API key is not configured. "
                "Set GCP_TTS_API_KEY or GEMINI_API_KEY in your .env file."
            )

        chosen_voice = voice_name or config.tts_voice_name or "en-US-Journey-F"
        chosen_rate = speaking_rate or config.tts_speaking_rate or 1.0

        # Infer language code from voice name (e.g. 'en-US-Journey-F' -> 'en-US')
        lang_code = "-".join(chosen_voice.split("-")[:2]) if "-" in chosen_voice else "en-US"

        payload = {
            "input": {"text": text.strip()},
            "voice": {
                "languageCode": lang_code,
                "name": chosen_voice,
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": chosen_rate,
                "sampleRateHertz": 24000,
            },
        }

        logger.info(
            "tts_synthesis_requested",
            provider="google_cloud_tts",
            voice=chosen_voice,
            chars=len(text),
        )

        response = requests.post(
            self.endpoint_url,
            params={"key": self.api_key},
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )

        if response.status_code != 200:
            err_msg = response.text
            if "Cloud Text-to-Speech API has not been used" in err_msg or "SERVICE_DISABLED" in err_msg:
                raise RuntimeError(
                    "Cloud Text-to-Speech API is not enabled for this Google Cloud project. "
                    "Please enable the 'Cloud Text-to-Speech API' in Google Cloud Console: "
                    "https://console.cloud.google.com/apis/library/texttospeech.googleapis.com"
                )
            raise RuntimeError(f"Google Cloud TTS API error ({response.status_code}): {err_msg}")

        data = response.json()
        audio_content_b64 = data.get("audioContent")
        if not audio_content_b64:
            raise ValueError(f"No audioContent returned by Google Cloud TTS: {data}")

        return base64.b64decode(audio_content_b64)


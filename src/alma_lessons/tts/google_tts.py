import base64
import os
import requests
from typing import Optional
import structlog
from .interface import BaseTTSClient
from ..config import config

logger = structlog.get_logger(__name__)


def _get_oauth2_token() -> Optional[str]:
    """Attempt to obtain an OAuth2 Bearer token from GCP Service Account JSON or ADC."""
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or config.gcp_service_account_json
    if creds_path and os.path.exists(creds_path):
        try:
            from google.oauth2 import service_account
            import google.auth.transport.requests

            scopes = ["https://www.googleapis.com/auth/cloud-platform"]
            creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
            req = google.auth.transport.requests.Request()
            creds.refresh(req)
            return creds.token
        except Exception as e:
            logger.warning("failed_to_load_gcp_service_account", error=str(e))

    try:
        import google.auth
        import google.auth.transport.requests

        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        req = google.auth.transport.requests.Request()
        creds.refresh(req)
        return creds.token
    except Exception:
        return None


class GoogleCloudTTSClient(BaseTTSClient):
    """Google Cloud Text-to-Speech REST client supporting Journey and Neural2 voices.
    Supports OAuth2 Service Account JSON credentials, direct Bearer tokens, or API keys,
    with automatic graceful fallback to zero-config Google TTS (gTTS) if GCP credentials are absent.
    """

    def __init__(self, api_key: Optional[str] = None, allow_fallback: bool = True):
        self.api_key = api_key or config.gcp_tts_api_key or config.gemini_api_key
        self.endpoint_url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        self.allow_fallback = allow_fallback

    def synthesize(
        self,
        text: str,
        voice_name: Optional[str] = None,
        speaking_rate: Optional[float] = None,
    ) -> bytes:
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

        # Check for OAuth2 access token first
        oauth_token = _get_oauth2_token()
        headers = {"Content-Type": "application/json"}
        params = {}

        if oauth_token:
            headers["Authorization"] = f"Bearer {oauth_token}"
        elif self.api_key:
            params["key"] = self.api_key
        elif not self.allow_fallback:
            raise ValueError(
                "Google Text-to-Speech credentials missing. Provide a Service Account JSON via "
                "GOOGLE_APPLICATION_CREDENTIALS or set TTS_PROVIDER=gtts for free voice."
            )

        if oauth_token or self.api_key:
            logger.info(
                "tts_synthesis_requested",
                provider="google_cloud_tts",
                voice=chosen_voice,
                chars=len(text),
                auth_mode="oauth2" if oauth_token else "api_key",
            )

            response = requests.post(
                self.endpoint_url,
                params=params,
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                audio_content_b64 = data.get("audioContent")
                if audio_content_b64:
                    return base64.b64decode(audio_content_b64)

            err_msg = response.text
            # If GCP rejects API key or credentials are missing
            if response.status_code in (401, 403) and self.allow_fallback:
                logger.warning(
                    "gcp_tts_unauthenticated_falling_back_to_gtts",
                    status_code=response.status_code,
                    reason="API keys not supported by GCP TTS without Service Account; using gTTS fallback.",
                )
                from .gtts_client import GTTSClient

                return GTTSClient().synthesize(text, voice_name=chosen_voice, speaking_rate=chosen_rate)

            if "Cloud Text-to-Speech API has not been used" in err_msg or "SERVICE_DISABLED" in err_msg:
                raise RuntimeError(
                    "Cloud Text-to-Speech API is not enabled for this Google Cloud project. "
                    "Enable it at: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com"
                )
            raise RuntimeError(f"Google Cloud TTS API error ({response.status_code}): {err_msg}")

        # If no credentials and fallback enabled
        if self.allow_fallback:
            from .gtts_client import GTTSClient

            return GTTSClient().synthesize(text, voice_name=chosen_voice, speaking_rate=chosen_rate)

        raise ValueError("No credentials found for Google Cloud TTS.")

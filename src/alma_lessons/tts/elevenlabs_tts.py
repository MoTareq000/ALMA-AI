import os
from typing import Optional, Dict
import requests
import structlog
from .interface import BaseTTSClient
from ..config import config

logger = structlog.get_logger(__name__)

# Curated Premade Voices (Available on all ElevenLabs tiers including Free)
ELEVENLABS_VOICE_MAP: Dict[str, str] = {
    "Alice (Clear & Engaging Educator)": "Xb7hH8MSUJpSbSDYk0k2",
    "Sarah (Mature, Reassuring & Confident)": "EXAVITQu4vr4xnSDxMaL",
    "Charlie (Deep, Confident & Energetic)": "IKne3meq5aSn9XLyUdCD",
    "George (Warm & Captivating Storyteller)": "JBFqnCBsd6RMkjVDRZzb",
    "Roger (Laid-Back, Casual & Resonant)": "CwhRBWXzGAHq8TQ4Fs17",
    "Laura (Enthusiastic & Quirky Attitude)": "FGY2WhTYpPnrIDTdsKH5",
    "River (Relaxed, Neutral & Informative)": "SAz9YHcvj6GT2YYXdXww",
    "Liam (Energetic Creator Tutor)": "TX3LPaxmHKxFdv7VOQHJ",
}

DEFAULT_VOICE_ID = "Xb7hH8MSUJpSbSDYk0k2"  # Alice (Clear & Engaging Educator)


class ElevenLabsTTSClient(BaseTTSClient):
    """ElevenLabs High-Definition Text-to-Speech client using ElevenLabs REST API.
    Provides ultra-realistic human speech.
    If API quota is exhausted (429/402) or request fails, seamlessly falls back to
    Microsoft Edge Neural voices to guarantee uninterrupted learning.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.elevenlabs_api_key or os.environ.get("ELEVENLABS_API_KEY", "")
        self.base_url = "https://api.elevenlabs.io/v1/text-to-speech"
        self.model_id = "eleven_turbo_v2_5"

    def _resolve_voice_id(self, voice_name: Optional[str]) -> str:
        if not voice_name:
            return DEFAULT_VOICE_ID
        if voice_name in ELEVENLABS_VOICE_MAP.values():
            return voice_name
        if voice_name in ELEVENLABS_VOICE_MAP:
            return ELEVENLABS_VOICE_MAP[voice_name]
        # Check by prefix / substring
        for name, vid in ELEVENLABS_VOICE_MAP.items():
            if voice_name.lower() in name.lower() or voice_name.lower() in vid.lower():
                return vid
        return DEFAULT_VOICE_ID

    def synthesize(
        self,
        text: str,
        voice_name: Optional[str] = None,
        speaking_rate: Optional[float] = None,
    ) -> bytes:
        clean_text = text.strip()
        if not clean_text:
            return b""

        voice_id = self._resolve_voice_id(voice_name)
        url = f"{self.base_url}/{voice_id}"

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

        payload = {
            "text": clean_text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        logger.info(
            "elevenlabs_tts_synthesis_requested",
            voice_id=voice_id,
            chars=len(clean_text),
            model=self.model_id,
        )

        try:
            if not self.api_key:
                raise ValueError("Missing ELEVENLABS_API_KEY")

            resp = requests.post(url, json=payload, headers=headers, timeout=20)

            if resp.status_code == 200:
                return resp.content

            logger.warning(
                "elevenlabs_api_non_200",
                status_code=resp.status_code,
                response_text=resp.text[:200],
            )

            # Try fallback model if turbo failed with 400
            if resp.status_code == 400:
                payload["model_id"] = "eleven_multilingual_v2"
                retry_resp = requests.post(url, json=payload, headers=headers, timeout=20)
                if retry_resp.status_code == 200:
                    return retry_resp.content

            raise RuntimeError(f"ElevenLabs API returned HTTP {resp.status_code}: {resp.text[:150]}")

        except Exception as e:
            logger.warning(
                "elevenlabs_tts_fallback_to_edge",
                error=str(e),
                detail="Falling back to Edge Neural voice (en-US-JennyNeural) seamlessly.",
            )
            from .edge_tts_client import EdgeTTSClient

            fallback_client = EdgeTTSClient()
            return fallback_client.synthesize(
                text=clean_text,
                voice_name="en-US-JennyNeural",
                speaking_rate=speaking_rate,
            )

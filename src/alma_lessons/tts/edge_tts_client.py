import asyncio
import concurrent.futures
from typing import Optional
import edge_tts
import structlog
from .interface import BaseTTSClient

logger = structlog.get_logger(__name__)


def _run_async_sync(coro):
    """Run an async coroutine synchronously, safe in both sync and running-loop contexts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


class EdgeTTSClient(BaseTTSClient):
    """Free, studio-grade Neural Text-to-Speech client using Microsoft Edge Neural voices.
    Requires ZERO API keys, ZERO credit cards, and ZERO cloud billing accounts.
    Available voices include:
        - en-US-JennyNeural (Warm, clear female teacher)
        - en-US-GuyNeural (Conversational, engaging male tutor)
        - en-US-AvaNeural (Modern, expressive studio female)
        - en-US-AndrewNeural (Confident, natural studio male)
        - en-US-AriaNeural (Professional pedagogical female)
        - en-US-ChristopherNeural (Enthusiastic male instructor)
        - en-GB-SoniaNeural (Polished British female)
        - en-GB-RyanNeural (Friendly British male)
    """

    def synthesize(
        self,
        text: str,
        voice_name: Optional[str] = None,
        speaking_rate: Optional[float] = None,
    ) -> bytes:
        chosen_voice = voice_name or "en-US-JennyNeural"

        # Map rate float to Edge TTS percentage string (e.g. 1.05 -> "+5%", 0.95 -> "-5%")
        rate_str = "+0%"
        if speaking_rate is not None and abs(speaking_rate - 1.0) > 0.01:
            diff = int(round((speaking_rate - 1.0) * 100))
            rate_str = f"{diff:+d}%"

        logger.info(
            "edge_tts_synthesis_requested",
            voice=chosen_voice,
            rate=rate_str,
            chars=len(text),
        )

        async def _synthesize():
            communicate = edge_tts.Communicate(text.strip(), chosen_voice, rate=rate_str)
            chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
            return b"".join(chunks)

        return _run_async_sync(_synthesize())


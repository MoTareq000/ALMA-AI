from pathlib import Path
from fastapi.testclient import TestClient
from alma_lessons.main import app
from alma_lessons.tts import AudioCacheManager, FakeTTSClient
from alma_lessons.domain import (
    LessonSpec,
    LessonContent,
    Section,
    Block,
    LessonSegmentation,
    TopicSegmentation,
    Segment,
)
from alma_lessons.storage import memory_store

client = TestClient(app)


def test_audio_cache_key_and_storage(tmp_path: Path):
    cache = AudioCacheManager(cache_dir=tmp_path)
    text = "Hello students, today we learn loops."
    key1 = cache.compute_cache_key(text, voice_name="en-US-Journey-F", speaking_rate=1.0)
    key2 = cache.compute_cache_key(text, voice_name="en-US-Journey-F", speaking_rate=1.0)
    assert key1 == key2

    # Save audio
    fake_bytes = b"\xff\xfb\x90\x00" + (b"\x00" * 100)
    saved_path = cache.save_audio(key1, fake_bytes)
    assert saved_path.is_file()
    assert cache.has_audio(key1) is True
    assert cache.get_audio_path(key1) == saved_path


def test_fake_tts_client():
    fake = FakeTTSClient()
    audio = fake.synthesize("Test text")
    assert isinstance(audio, bytes)
    assert len(audio) > 0


def test_audio_streaming_endpoints(tmp_path: Path):
    # Test 404 for missing file
    r = client.get("/api/v1/audio/nonexistent_12345.mp3")
    assert r.status_code == 404

    # Test invalid extension
    r = client.get("/api/v1/audio/malicious.txt")
    assert r.status_code == 400

    # Create dummy lesson with segmentation in memory store
    spec = LessonSpec(
        subject="Programming",
        topic="Audio Test Topic",
        programming_language="Python",
        grade_level="Grade 7",
        learning_objectives=["Understand audio"],
    )
    content = LessonContent(
        title="Audio Test Lesson",
        programming_language="Python",
        grade_level="Grade 7",
        target_duration_minutes=10,
        introduction=[Block(type="paragraph", text="Welcome.")],
        objectives=["Understand audio"],
        sections=[Section(order=1, title="Intro", purpose="Explain", blocks=[Block(type="paragraph", text="Loops repeat.")])],
        conclusion=[Block(type="paragraph", text="Done.")],
    )
    seg = Segment(
        topic_title="Intro",
        order_in_topic=1,
        order_in_lesson=1,
        title="Intro - Part 1",
        narration_text="Here is our first narrated audio segment.",
        word_count=7,
        est_seconds=5.0,
    )
    segmentation = LessonSegmentation(
        lesson_title="Audio Test Lesson",
        total_segments=1,
        est_total_duration_minutes=0.5,
        topics=[TopicSegmentation(topic_title="Intro", order=1, purpose="Explain", segments=[seg])],
    )

    session = memory_store.create_lesson(spec=spec, content=content, segmentation=segmentation)
    lesson_id = session.lesson_id

    # Synthesize using fake provider (cost-free, offline)
    resp = client.post(f"/api/v1/lessons/{lesson_id}/synthesize-audio?provider=fake")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["total_segments"] == 1

    # Verify segment has audio_file and audio_url
    updated_session = memory_store.lessons.get(lesson_id)
    updated_seg = updated_session.current_version.segmentation.topics[0].segments[0]
    assert updated_seg.audio_file is not None
    assert updated_seg.audio_url is not None

    # Fetch the audio file through the streaming endpoint
    audio_resp = client.get(updated_seg.audio_url)
    assert audio_resp.status_code == 200
    assert audio_resp.headers["content-type"] == "audio/mpeg"
    assert len(audio_resp.content) > 0


"""
transcriber.py — Groq Whisper fallback khi YouTube không có subtitle
"""
import os
from groq import Groq
from .downloader import SubtitleEntry


def transcribe_with_groq(audio_path: str) -> list[SubtitleEntry]:
    """
    Dùng Groq Whisper API để transcribe audio thành subtitle có timestamp.
    Miễn phí: 14,400 phút/ngày.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Cần set GROQ_API_KEY trong .env")

    client = Groq(api_key=api_key)

    print(f"🎙️  Đang transcribe với Groq Whisper: {audio_path}")
    
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), f),
            model="whisper-large-v3",
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    entries = []
    if hasattr(transcription, "segments") and transcription.segments:
        for seg in transcription.segments:
            text = seg.get("text", "").strip()
            if text:
                entries.append(SubtitleEntry(
                    start=seg.get("start", 0.0),
                    end=seg.get("end", 0.0),
                    text=text,
                ))
    
    print(f"✅ Transcribed {len(entries)} segments")
    return entries

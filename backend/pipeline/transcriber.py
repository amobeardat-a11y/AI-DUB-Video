"""
transcriber.py — Groq Whisper fallback khi YouTube không có subtitle
"""
import os
from .downloader import SubtitleEntry


def transcribe_with_groq(audio_path: str) -> list[SubtitleEntry]:
    """
    Dùng Groq Whisper API để transcribe audio thành subtitle có timestamp.
    Miễn phí: 14,400 phút/ngày.
    """
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Cần set GROQ_API_KEY trong .env")

    client = Groq(api_key=api_key)

    # Ép ngôn ngữ nguồn để Whisper nhận đúng (mặc định zh cho video Trung)
    source_lang = os.getenv("SOURCE_LANG", "zh")

    print(f"🎙️  Đang transcribe với Groq Whisper [{source_lang}]: {audio_path}")
    
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), f),
            model="whisper-large-v3",
            language=source_lang,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    entries = []
    segments = getattr(transcription, "segments", None)
    if segments:
        for seg in segments:
            # Groq SDK có thể trả segment dạng object hoặc dict tùy version
            if isinstance(seg, dict):
                text = (seg.get("text") or "").strip()
                start = seg.get("start", 0.0)
                end = seg.get("end", 0.0)
            else:
                text = (getattr(seg, "text", "") or "").strip()
                start = getattr(seg, "start", 0.0)
                end = getattr(seg, "end", 0.0)
            if text:
                entries.append(SubtitleEntry(
                    start=float(start),
                    end=float(end),
                    text=text,
                ))
    
    print(f"✅ Transcribed {len(entries)} segments")
    return entries

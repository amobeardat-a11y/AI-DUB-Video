"""
tts_engine.py — Text-to-Speech tiếng Việt dùng Edge-TTS
Voice: vi-VN-HoaiMyNeural (nữ) hoặc vi-VN-NamMinhNeural (nam)
"""
import os
import asyncio
import subprocess
from pathlib import Path
from .downloader import SubtitleEntry


VOICE = os.getenv("TTS_VOICE", "vi-VN-HoaiMyNeural")


async def _tts_async(text: str, output_path: str, voice: str):
    """Tạo audio từ text bằng Edge-TTS async."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_segment_audio(
    text: str,
    output_path: str,
    voice: str = VOICE,
) -> str:
    """Tạo file audio MP3 cho một đoạn text."""
    asyncio.run(_tts_async(text, output_path, voice))
    return output_path


def generate_all_segments(
    subtitles: list[SubtitleEntry],
    segments_dir: str,
    voice: str = VOICE,
) -> list[dict]:
    """
    Tạo audio riêng cho từng subtitle entry.
    Trả về list[{start, end, audio_path, original_duration, text}]
    """
    segments_dir = Path(segments_dir)
    segments_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔊 Tạo TTS cho {len(subtitles)} segments (voice: {voice})...")
    
    results = []
    for i, entry in enumerate(subtitles):
        seg_path = str(segments_dir / f"seg_{i:04d}.mp3")
        
        # Skip nếu text rỗng
        if not entry.text.strip():
            continue
        
        try:
            generate_segment_audio(entry.text, seg_path, voice)
            
            # Lấy duration thực tế của audio
            audio_duration = _get_audio_duration(seg_path)
            target_duration = entry.end - entry.start
            
            results.append({
                "index": i,
                "start": entry.start,
                "end": entry.end,
                "target_duration": target_duration,
                "audio_duration": audio_duration,
                "audio_path": seg_path,
                "text": entry.text,
            })
            
            if (i + 1) % 10 == 0:
                print(f"  ✅ {i+1}/{len(subtitles)} segments done")
                
        except Exception as e:
            print(f"  ⚠️  Segment {i} lỗi: {e}")
    
    print(f"✅ TTS xong: {len(results)} segments")
    return results


def _get_audio_duration(audio_path: str) -> float:
    """Lấy duration của audio file bằng ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        import json
        data = json.loads(result.stdout)
        for stream in data.get("streams", []):
            if "duration" in stream:
                return float(stream["duration"])
    return 0.0

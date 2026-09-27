"""
tts_engine.py — Text-to-Speech tiếng Việt (pluggable engine)
TTS_ENGINE=vieneu -> VieNeu-TTS on-device (neural, mặc định). Fallback Edge-TTS khi lỗi.
TTS_ENGINE=edge   -> Edge-TTS cloud (nhẹ). Voice: vi-VN-HoaiMyNeural / vi-VN-NamMinhNeural
"""
import os
import asyncio
import subprocess
from pathlib import Path
from .downloader import SubtitleEntry


TTS_ENGINE = os.getenv("TTS_ENGINE", "vieneu").lower()
VOICE = os.getenv("TTS_VOICE", "vi-VN-HoaiMyNeural")
VIENEU_VOICE = os.getenv("VIENEU_VOICE", "Hải Đăng")
# Voice Edge-TTS dùng khi fallback (VieNeu voice không dùng được cho Edge)
EDGE_FALLBACK_VOICE = os.getenv("EDGE_FALLBACK_VOICE", "vi-VN-HoaiMyNeural")

# Model VieNeu load 1 lần rồi tái sử dụng (init tốn ~15-20s trên CPU)
_vieneu_model = None


def _get_vieneu():
    """Lazy-load singleton model VieNeu-TTS."""
    global _vieneu_model
    if _vieneu_model is None:
        from vieneu import Vieneu
        print("🔊 Đang load model VieNeu-TTS (lần đầu ~15-20s trên CPU)...")
        _vieneu_model = Vieneu()
    return _vieneu_model


async def _tts_edge_async(text: str, output_path: str, voice: str):
    """Tạo audio từ text bằng Edge-TTS async."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def _tts_vieneu(text: str, output_path: str, voice: str):
    """Tạo audio bằng VieNeu-TTS on-device."""
    model = _get_vieneu()
    # Voice mặc định của pipeline là tên Edge-TTS; VieNeu cần tên giọng riêng.
    vieneu_voice = voice if voice and not voice.startswith("vi-VN") else VIENEU_VOICE
    audio = model.infer(text, voice=vieneu_voice)
    model.save(audio, output_path)


def generate_segment_audio(
    text: str,
    output_path: str,
    voice: str = VOICE,
) -> str:
    """Tạo file audio cho một đoạn text. VieNeu chính, Edge-TTS fallback khi lỗi."""
    if TTS_ENGINE == "vieneu":
        try:
            _tts_vieneu(text, output_path, voice)
        except Exception as e:
            print(f"  ⚠️  VieNeu lỗi ({e}) → fallback Edge-TTS")
            asyncio.run(_tts_edge_async(text, output_path, EDGE_FALLBACK_VOICE))
    else:
        asyncio.run(_tts_edge_async(text, output_path, voice))
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
    
    # VieNeu xuất wav; Edge-TTS xuất mp3. FFmpeg đọc theo nội dung nên fallback vẫn ok.
    ext = "wav" if TTS_ENGINE == "vieneu" else "mp3"
    voice_label = VIENEU_VOICE if TTS_ENGINE == "vieneu" else voice
    print(f"🔊 Tạo TTS cho {len(subtitles)} segments (engine: {TTS_ENGINE}, voice: {voice_label})...")
    
    results = []
    for i, entry in enumerate(subtitles):
        seg_path = str(segments_dir / f"seg_{i:04d}.{ext}")
        
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

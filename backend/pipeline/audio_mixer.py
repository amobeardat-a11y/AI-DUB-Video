"""
audio_mixer.py — Ghép TTS audio vào video dùng FFmpeg
- Điều chỉnh tốc độ TTS khớp với timestamp
- Giảm âm gốc xuống 12% (giữ âm nhạc nền)
- Mix TTS + âm gốc giảm âm
"""
import os
import subprocess
import json
from pathlib import Path
from typing import Optional


ORIGINAL_AUDIO_VOL = float(os.getenv("ORIGINAL_AUDIO_VOLUME", "0.12"))


def mix_audio_to_video(
    video_path: str,
    segments: list[dict],
    output_path: str,
    original_vol: float = ORIGINAL_AUDIO_VOL,
    temp_dir: Optional[str] = None,
) -> str:
    """
    Ghép toàn bộ TTS segments vào video.
    
    Args:
        video_path: Path đến video MP4 gốc
        segments: List segment từ tts_engine.generate_all_segments()
        output_path: Path video output
        original_vol: Volume của audio gốc (0.12 = 12%)
        temp_dir: Thư mục tạm
    
    Returns:
        Path đến video output đã ghép
    """
    if not segments:
        raise ValueError("Không có TTS segments để ghép")
    
    video_path = Path(video_path)
    output_path = Path(output_path)
    temp_dir = Path(temp_dir or video_path.parent / "temp_audio")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🎬 Bắt đầu mix audio cho {len(segments)} segments...")
    
    # Bước 1: Lấy total video duration
    video_duration = _get_video_duration(str(video_path))
    print(f"   Video duration: {video_duration:.1f}s")
    
    # Bước 2: Tạo silent base audio cùng độ dài video
    silent_path = str(temp_dir / "silent_base.wav")
    _create_silent_audio(video_duration, silent_path)
    
    # Bước 3: Overlay từng TTS segment lên silent base
    dubbed_audio_path = str(temp_dir / "dubbed_audio.wav")
    _overlay_segments(segments, silent_path, dubbed_audio_path, video_duration)
    
    # Bước 4: Lấy audio gốc, giảm volume
    original_audio_path = str(temp_dir / "original_low.wav")
    _extract_and_lower_original_audio(str(video_path), original_audio_path, original_vol)
    
    # Bước 5: Mix dubbed + original_low
    mixed_audio_path = str(temp_dir / "final_mixed.wav")
    _mix_two_audios(dubbed_audio_path, original_audio_path, mixed_audio_path)
    
    # Bước 6: Ghép mixed audio vào video gốc
    _combine_video_audio(str(video_path), mixed_audio_path, str(output_path))
    
    print(f"✅ Video đã xuất: {output_path}")
    return str(output_path)


def _get_video_duration(video_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data["format"].get("duration", 0))


def _create_silent_audio(duration: float, output_path: str):
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration),
        "-acodec", "pcm_s16le",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def _overlay_segments(
    segments: list[dict],
    base_audio: str,
    output_path: str,
    video_duration: float,
):
    """Overlay từng TTS segment lên base audio theo đúng timestamp."""
    # Xây dựng filter_complex cho ffmpeg
    # Input 0: base silent audio
    # Input 1..N: các segment TTS
    
    inputs = ["-i", base_audio]
    for seg in segments:
        inputs += ["-i", seg["audio_path"]]
    
    # Xây dựng filter graph
    filter_parts = []
    current_label = "[0:a]"
    
    for i, seg in enumerate(segments):
        input_label = f"[{i+1}:a]"
        out_label = f"[mix{i}]"
        
        # Tính tempo để khớp thời gian
        target_dur = seg["target_duration"]
        audio_dur = seg["audio_duration"]
        
        if audio_dur > 0 and target_dur > 0:
            tempo = audio_dur / target_dur
            # FFmpeg atempo chỉ hỗ trợ 0.5-2.0
            tempo = max(0.5, min(2.0, tempo))
            tempo_filter = f"atempo={tempo:.4f}"
        else:
            tempo_filter = "atempo=1.0"
        
        # Pad segment để đúng vị trí
        delay_ms = int(seg["start"] * 1000)
        
        filter_parts.append(
            f"{input_label}aresample=44100,{tempo_filter},apad=pad_dur={video_duration}[seg{i}]"
        )
        filter_parts.append(
            f"[seg{i}]adelay={delay_ms}|{delay_ms}[delayed{i}]"
        )
        filter_parts.append(
            f"{current_label}[delayed{i}]amix=inputs=2:normalize=0{out_label}"
        )
        current_label = out_label
    
    filter_complex = ";".join(filter_parts)
    
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", current_label,
        "-t", str(video_duration),
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback: dùng concat approach đơn giản hơn
        print("⚠️  Complex filter thất bại, dùng approach đơn giản hơn...")
        _overlay_segments_simple(segments, base_audio, output_path, video_duration)


def _overlay_segments_simple(
    segments: list[dict],
    base_audio: str,
    output_path: str,
    video_duration: float,
):
    """Simple overlay: merge tất cả segment với delay."""
    import shutil
    current = base_audio
    
    for i, seg in enumerate(segments):
        out = output_path + f".tmp{i}.wav"
        delay_ms = int(seg["start"] * 1000)
        
        target_dur = seg["target_duration"]
        audio_dur = seg["audio_duration"]
        if audio_dur > 0 and target_dur > 0:
            tempo = max(0.5, min(2.0, audio_dur / target_dur))
        else:
            tempo = 1.0
        
        cmd = [
            "ffmpeg", "-y",
            "-i", current,
            "-i", seg["audio_path"],
            "-filter_complex",
            f"[1:a]atempo={tempo:.4f},adelay={delay_ms}|{delay_ms}[seg];[0:a][seg]amix=inputs=2:normalize=0",
            "-t", str(video_duration),
            "-acodec", "pcm_s16le",
            out
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            if current != base_audio and os.path.exists(current):
                os.remove(current)
            current = out
        else:
            print(f"  ⚠️  Segment {i} overlay thất bại, bỏ qua")
    
    if current != output_path:
        import shutil
        shutil.copy2(current, output_path)
        if current != base_audio:
            os.remove(current)


def _extract_and_lower_original_audio(video_path: str, output_path: str, volume: float):
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn",
        "-af", f"volume={volume}",
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def _mix_two_audios(audio1: str, audio2: str, output_path: str):
    cmd = [
        "ffmpeg", "-y",
        "-i", audio1, "-i", audio2,
        "-filter_complex", "amix=inputs=2:normalize=0",
        "-acodec", "pcm_s16le",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def _combine_video_audio(video_path: str, audio_path: str, output_path: str):
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-acodec", "aac",
        "-b:a", "192k",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg ghép video thất bại:\n{result.stderr[-500:]}")

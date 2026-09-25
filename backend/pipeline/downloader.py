"""
downloader.py — Tải video YouTube và lấy subtitle
Ưu tiên: subtitle YouTube gốc → Groq Whisper fallback
"""
import os
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import yt_dlp


@dataclass
class SubtitleEntry:
    start: float   # seconds
    end: float     # seconds
    text: str


@dataclass
class DownloadResult:
    video_path: str
    audio_path: str
    subtitles: list[SubtitleEntry]
    source: str  # "youtube_sub" | "whisper"
    title: str
    duration: float


def parse_vtt_time(ts: str) -> float:
    """Convert VTT timestamp '00:01:23.456' to seconds."""
    ts = ts.strip()
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
    else:
        h, m, s = 0, parts[0], parts[1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_vtt_content(vtt_text: str) -> list[SubtitleEntry]:
    """Parse WebVTT subtitle file into list of SubtitleEntry."""
    entries = []
    lines = vtt_text.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "-->" in line:
            try:
                start_str, end_str = line.split("-->")
                # Remove positioning info
                end_str = end_str.split(" ")[0]
                start = parse_vtt_time(start_str)
                end = parse_vtt_time(end_str)
                # Collect text lines
                text_lines = []
                i += 1
                while i < len(lines) and lines[i].strip() != "":
                    text_lines.append(lines[i].strip())
                    i += 1
                text = " ".join(text_lines)
                # Clean HTML tags
                import re
                text = re.sub(r"<[^>]+>", "", text).strip()
                if text:
                    entries.append(SubtitleEntry(start=start, end=end, text=text))
            except Exception:
                pass
        i += 1
    return entries


def download_video(url: str, output_dir: str = "./output") -> DownloadResult:
    """
    Tải video YouTube + lấy subtitle.
    Returns DownloadResult với đầy đủ thông tin.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # === Bước 1: Lấy thông tin video ===
    print(f"🔍 Đang lấy thông tin video: {url}")
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    
    video_id = info.get("id", "unknown")
    title = info.get("title", "video")
    duration = info.get("duration", 0)
    
    # Tên file an toàn
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:50]
    base_path = output_dir / f"{video_id}_{safe_title}"
    video_path = str(base_path) + ".mp4"
    audio_path = str(base_path) + "_audio.wav"
    sub_path = str(base_path) + ".vtt"

    print(f"📹 Title: {title}")
    print(f"⏱️  Duration: {duration}s")

    # === Bước 2: Download video + thử lấy subtitle YTB ===
    print("⬇️  Đang tải video...")
    
    ydl_opts = {
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
        "outtmpl": str(base_path) + ".%(ext)s",
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "vi"],
        "subtitlesformat": "vtt",
        "merge_output_format": "mp4",
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
        "quiet": False,
        "no_warnings": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Tìm video file (yt-dlp có thể đặt tên khác)
    found_video = None
    for f in output_dir.glob(f"{video_id}*.mp4"):
        if "_audio" not in str(f):
            found_video = str(f)
            break
    if not found_video and Path(video_path).exists():
        found_video = video_path
    if not found_video:
        raise FileNotFoundError(f"Không tìm thấy video sau khi tải: {base_path}*.mp4")
    video_path = found_video

    # === Bước 3: Extract audio để Whisper fallback ===
    print("🎵 Đang extract audio...")
    _extract_audio(video_path, audio_path)

    # === Bước 4: Tìm subtitle YTB ===
    subtitles = []
    sub_source = "whisper"

    # Tìm file .vtt được tải về (en trước, vi sau)
    for lang in ["en", "vi"]:
        for vtt_file in output_dir.glob(f"{video_id}*.{lang}.vtt"):
            print(f"✅ Tìm thấy subtitle YouTube ({lang}): {vtt_file.name}")
            with open(vtt_file, encoding="utf-8") as f:
                vtt_content = f.read()
            subtitles = parse_vtt_content(vtt_content)
            if subtitles:
                sub_source = f"youtube_sub_{lang}"
                break
        if subtitles:
            break

    if not subtitles:
        print("⚠️  Không có subtitle YouTube. Sẽ dùng Groq Whisper để transcribe...")
        # Groq Whisper fallback sẽ được gọi từ pipeline chính
        sub_source = "whisper_pending"

    print(f"📊 Subtitle: {len(subtitles)} entries từ [{sub_source}]")
    
    return DownloadResult(
        video_path=video_path,
        audio_path=audio_path,
        subtitles=subtitles,
        source=sub_source,
        title=title,
        duration=duration,
    )


def _extract_audio(video_path: str, audio_path: str):
    """Extract audio WAV từ video dùng ffmpeg."""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg extract audio thất bại:\n{result.stderr}")
    print(f"✅ Audio extracted: {audio_path}")

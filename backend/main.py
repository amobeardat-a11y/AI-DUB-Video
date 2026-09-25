"""
main.py — VietDub Auto: CLI Pipeline chính
Usage: python main.py --url "https://youtube.com/watch?v=..." [options]

Pipeline:
  1. Download video + subtitle YouTube
  2. Transcribe bằng Groq Whisper (nếu không có sub)
  3. Dịch sang tiếng Việt (Gemini → Google Translate)
  4. TTS (Edge-TTS vi-VN-HoaiMyNeural)
  5. Mix audio vào video (FFmpeg)
  6. Upload lên YouTube/Facebook (tùy chọn)
"""
import os
import sys
import shutil
import argparse
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.downloader import download_video
from pipeline.transcriber import transcribe_with_groq
from pipeline.translator import translate_subtitles, export_srt
from pipeline.tts_engine import generate_all_segments
from pipeline.audio_mixer import mix_audio_to_video


def check_ffmpeg():
    """Kiểm tra ffmpeg có trong PATH không."""
    result = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not result:
        print("❌ FFmpeg chưa được cài hoặc chưa thêm vào PATH!")
        print("   Tải tại: https://ffmpeg.org/download.html")
        print("   Hoặc: winget install ffmpeg")
        sys.exit(1)
    print(f"✅ FFmpeg: {result}")


def run_pipeline(
    url: str,
    output_dir: str = "./output",
    upload_youtube: bool = False,
    upload_facebook: bool = False,
    keep_temp: bool = False,
    voice: str = None,
):
    """
    Chạy toàn bộ pipeline VietDub.
    
    Args:
        url: YouTube URL
        output_dir: Thư mục output
        upload_youtube: Tự động upload lên YouTube
        upload_facebook: Tự động upload lên Facebook
        keep_temp: Giữ lại file tạm (debug)
        voice: Edge-TTS voice name
    """
    start_time = time.time()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print("🎬 VietDub Auto — Starting Pipeline")
    print("="*60)
    print(f"📎 URL: {url}")
    print(f"📁 Output: {output_dir.absolute()}")
    print("="*60 + "\n")
    
    # ===== STEP 1: Download =====
    print("\n[1/5] 📥 DOWNLOADING VIDEO...")
    result = download_video(url, str(output_dir))
    
    video_id = Path(result.video_path).stem.split("_")[0]
    temp_dir = output_dir / f"temp_{video_id}"
    segments_dir = temp_dir / "segments"
    
    # ===== STEP 2: Transcribe (nếu cần) =====
    subtitles = result.subtitles
    
    if result.source == "whisper_pending":
        print("\n[2/5] 🎙️  TRANSCRIBING WITH GROQ WHISPER...")
        subtitles = transcribe_with_groq(result.audio_path)
    else:
        print(f"\n[2/5] ✅ Đã có subtitle YouTube ({result.source}), bỏ qua transcribe")
    
    if not subtitles:
        print("❌ Không có subtitle để xử lý!")
        return None
    
    # ===== STEP 3: Translate =====
    print(f"\n[3/5] 🌐 TRANSLATING {len(subtitles)} ENTRIES TO VIETNAMESE...")
    vi_subtitles = translate_subtitles(subtitles, video_title=result.title)
    
    # Export SRT
    srt_path = str(output_dir / f"{video_id}_vi.srt")
    export_srt(vi_subtitles, srt_path)
    
    # ===== STEP 4: TTS =====
    print(f"\n[4/5] 🔊 GENERATING TTS AUDIO...")
    voice_name = voice or os.getenv("TTS_VOICE", "vi-VN-HoaiMyNeural")
    tts_segments = generate_all_segments(vi_subtitles, str(segments_dir), voice=voice_name)
    
    if not tts_segments:
        print("❌ TTS không tạo được audio!")
        return None
    
    # ===== STEP 5: Mix & Render =====
    print(f"\n[5/5] 🎬 MIXING AUDIO & RENDERING VIDEO...")
    safe_title = "".join(c for c in result.title if c.isalnum() or c in " -_")[:40].strip()
    output_video_path = str(output_dir / f"{video_id}_vietdub_{safe_title}.mp4")
    
    mix_audio_to_video(
        video_path=result.video_path,
        segments=tts_segments,
        output_path=output_video_path,
        temp_dir=str(temp_dir),
    )
    
    # ===== STEP 6: Upload (tùy chọn) =====
    yt_video_id = None
    fb_video_id = None
    
    if upload_youtube:
        print("\n[6a] 📺 UPLOADING TO YOUTUBE...")
        try:
            from uploaders.youtube_uploader import upload_to_youtube
            yt_video_id = upload_to_youtube(
                video_path=output_video_path,
                title=result.title,
                privacy="private",  # private để review trước
            )
        except Exception as e:
            print(f"❌ YouTube upload thất bại: {e}")
    
    if upload_facebook:
        print("\n[6b] 📘 UPLOADING TO FACEBOOK...")
        try:
            from uploaders.facebook_uploader import upload_to_facebook
            fb_video_id = upload_to_facebook(
                video_path=output_video_path,
                title=result.title,
            )
        except Exception as e:
            print(f"❌ Facebook upload thất bại: {e}")
    
    # Cleanup temp
    if not keep_temp and temp_dir.exists():
        shutil.rmtree(temp_dir)
        print(f"\n🧹 Đã xóa temp files: {temp_dir}")
    
    # ===== Summary =====
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print("✅ PIPELINE HOÀN THÀNH!")
    print("="*60)
    print(f"⏱️  Thời gian xử lý: {elapsed:.0f}s ({elapsed/60:.1f} phút)")
    print(f"🎬 Video output: {output_video_path}")
    print(f"📝 Subtitle SRT: {srt_path}")
    if yt_video_id:
        print(f"📺 YouTube: https://youtube.com/watch?v={yt_video_id}")
    if fb_video_id:
        print(f"📘 Facebook: https://facebook.com/{fb_video_id}")
    print("="*60 + "\n")
    
    return output_video_path


def main():
    parser = argparse.ArgumentParser(
        description="VietDub Auto — Tự động lồng tiếng Việt cho video YouTube",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python main.py --url "https://youtube.com/watch?v=dQw4w9WgXcQ"
  python main.py --url "https://youtu.be/dQw4w9WgXcQ" --upload-youtube --upload-facebook
  python main.py --url "..." --voice vi-VN-NamMinhNeural --output ./my_videos
        """
    )
    parser.add_argument("--url", "-u", required=True, help="YouTube URL")
    parser.add_argument("--output", "-o", default="./output", help="Thư mục output (default: ./output)")
    parser.add_argument("--upload-youtube", action="store_true", help="Tự động upload lên YouTube")
    parser.add_argument("--upload-facebook", action="store_true", help="Tự động upload lên Facebook")
    parser.add_argument("--keep-temp", action="store_true", help="Giữ lại file tạm để debug")
    parser.add_argument("--voice", default=None, 
                       help="Edge-TTS voice (default: vi-VN-HoaiMyNeural | vi-VN-NamMinhNeural)")
    
    args = parser.parse_args()
    
    # Kiểm tra FFmpeg
    check_ffmpeg()
    
    # Chạy pipeline
    run_pipeline(
        url=args.url,
        output_dir=args.output,
        upload_youtube=args.upload_youtube,
        upload_facebook=args.upload_facebook,
        keep_temp=args.keep_temp,
        voice=args.voice,
    )


if __name__ == "__main__":
    main()

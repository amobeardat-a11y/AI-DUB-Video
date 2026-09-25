# Changelog

Tất cả thay đổi đáng chú ý của dự án được ghi chép ở đây.

Format theo [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
versioning theo [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Batch processing nhiều URL cùng lúc
- Voice cloning — giữ giọng diễn viên gốc
- Auto-generate thumbnail tiếng Việt
- Telegram Bot interface

---

## [1.0.0] - 2024-09-25

### Added
- 🎬 Core pipeline: download → transcribe → translate → TTS → mix → render
- 📥 yt-dlp downloader với subtitle YouTube ưu tiên
- 🎙️ Groq Whisper fallback khi không có subtitle
- 🌐 Gemini AI translation + Google Translate fallback
- 🔊 Edge-TTS với giọng `vi-VN-HoaiMyNeural` và `vi-VN-NamMinhNeural`
- 🎚️ FFmpeg audio mixer: điều chỉnh tempo, mix âm gốc 12%
- 📺 YouTube Data API v3 upload
- 📘 Facebook Graph API upload (resumable)
- 🌐 Web UI với realtime progress qua WebSocket
- ⚡ FastAPI backend
- 🐳 Docker + Docker Compose support
- 📋 GitHub Actions CI/CD
- 🪟 Windows `start.bat` launcher

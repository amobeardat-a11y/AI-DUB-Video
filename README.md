<div align="center">

<img src="https://raw.githubusercontent.com/YOUR_USERNAME/vietdub-auto/main/docs/logo.png" alt="VietDub Auto" width="120" />

# 🎬 VietDub Auto

**Tự động lồng tiếng Việt cho video YouTube trong vài phút**

[![CI](https://github.com/YOUR_USERNAME/vietdub-auto/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/vietdub-auto/actions/workflows/ci.yml)
[![Docker](https://github.com/YOUR_USERNAME/vietdub-auto/actions/workflows/docker.yml/badge.svg)](https://github.com/YOUR_USERNAME/vietdub-auto/actions/workflows/docker.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub Stars](https://img.shields.io/github/stars/YOUR_USERNAME/vietdub-auto?style=social)](https://github.com/YOUR_USERNAME/vietdub-auto/stargazers)

[Demo](#-demo) · [Cài đặt](#-cài-đặt-nhanh) · [Tính năng](#-tính-năng) · [Roadmap](#-roadmap) · [Đóng góp](#-đóng-góp)

---

</div>

## 🎥 Demo

> Paste link YouTube → Video lồng tiếng Việt xuất hiện trong vài phút

```
Input:  https://youtube.com/watch?v=dQw4w9WgXcQ  (tiếng Anh)
           ↓  ~3 phút xử lý
Output: output/vietdub_Never_Gonna_Give_You_Up.mp4  🇻🇳
```

**Pipeline tự động:**

```
YouTube URL
    │
    ├─► [1] yt-dlp          → Tải video + subtitle YouTube
    │         ↓ (nếu không có sub)
    │   [2] Groq Whisper    → Transcribe audio → text
    │
    ├─► [3] Gemini AI       → Dịch sang tiếng Việt tự nhiên
    │
    ├─► [4] Edge-TTS        → Giọng đọc vi-VN-HoaiMyNeural
    │
    ├─► [5] FFmpeg          → Mix audio, giữ nhạc nền 12%
    │
    └─► [6] YouTube / FB API → Auto upload (tùy chọn)
```

---

## ✨ Tính Năng

| Tính năng | Mô tả |
|---|---|
| 🎯 **Smart subtitle** | Ưu tiên subtitle YouTube gốc, fallback Groq Whisper |
| 🧠 **AI Translation** | Gemini hiểu ngữ cảnh → dịch tự nhiên, không cứng nhắc |
| 🔊 **TTS chất lượng cao** | Edge-TTS giọng `vi-VN-HoaiMyNeural` / `NamMinhNeural` |
| 🎚️ **Smart audio mix** | Giữ nhạc nền gốc 12%, TTS rõ ràng |
| ⚡ **Tempo adjustment** | FFmpeg tự điều chỉnh tốc độ đọc khớp timestamp |
| 📺 **Auto upload** | YouTube Data API v3 + Facebook Graph API |
| 🌐 **Web UI** | Giao diện paste link, theo dõi tiến độ realtime |
| 🐳 **Docker ready** | Chạy 1 lệnh, không cần cài thủ công |

---

## 🚀 Cài Đặt Nhanh

### Yêu cầu
- Python **3.11+**
- [FFmpeg](https://ffmpeg.org/download.html) (thêm vào PATH)
- API key: [Gemini](https://aistudio.google.com) (miễn phí)

### Option A — Docker (Khuyến nghị, 1 lệnh)

```bash
# Clone repo
git clone https://github.com/YOUR_USERNAME/vietdub-auto.git
cd vietdub-auto

# Cấu hình API keys
cp .env.example .env
# Mở .env và điền GEMINI_API_KEY

# Chạy
docker compose up -d

# Mở http://localhost:80
```

### Option B — Local Python

```bash
git clone https://github.com/YOUR_USERNAME/vietdub-auto.git
cd vietdub-auto

# Cài dependencies
pip install -r requirements.txt

# Cấu hình
cp .env.example backend/.env
# Điền API keys vào backend/.env

# Chạy CLI
python backend/main.py --url "https://youtu.be/VIDEO_ID"

# Hoặc chạy Web UI
python backend/api/server.py
# Mở frontend/index.html
```

### Option C — Windows (1 click)

```
Chạy start.bat
```

---

## 📖 Sử Dụng

### CLI

```bash
# Cơ bản
python backend/main.py --url "https://youtube.com/watch?v=VIDEO_ID"

# Với giọng nam
python backend/main.py --url "..." --voice vi-VN-NamMinhNeural

# Auto upload sau khi xử lý
python backend/main.py --url "..." --upload-youtube --upload-facebook

# Chỉ định thư mục output
python backend/main.py --url "..." --output ./my_videos

# Debug (giữ temp files)
python backend/main.py --url "..." --keep-temp
```

### API (FastAPI)

```bash
# Tạo job mới
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtu.be/...", "voice": "vi-VN-HoaiMyNeural"}'

# Response: {"job_id": "abc123", "status": "pending", ...}

# Theo dõi qua WebSocket
wscat -c ws://localhost:8000/ws/abc123

# Download video sau khi xong
curl -O http://localhost:8000/download/abc123
```

---

## ⚙️ Cấu Hình

Tất cả cấu hình trong file `.env`:

```env
# === Bắt buộc ===
GEMINI_API_KEY=your_key_here      # https://aistudio.google.com

# === Tùy chọn ===
GROQ_API_KEY=your_key_here        # Cần nếu video không có subtitle

# === TTS ===
TTS_VOICE=vi-VN-HoaiMyNeural     # hoặc vi-VN-NamMinhNeural

# === Video ===
ORIGINAL_AUDIO_VOLUME=0.12        # 12% âm gốc giữ lại
VIDEO_QUALITY=720                  # 480 | 720 | 1080

# === Upload YouTube (tùy chọn) ===
YOUTUBE_CLIENT_SECRETS_FILE=client_secrets.json

# === Upload Facebook (tùy chọn) ===
FACEBOOK_PAGE_ID=your_page_id
FACEBOOK_ACCESS_TOKEN=your_token
```

---

## 🔑 Setup Upload

<details>
<summary>📺 YouTube Upload</summary>

1. Vào [Google Cloud Console](https://console.cloud.google.com)
2. Tạo project → Enable **YouTube Data API v3**
3. Credentials → Create **OAuth 2.0 Client ID** (Desktop app)
4. Download JSON → đổi tên thành `client_secrets.json` → đặt vào `backend/`
5. Chạy lần đầu: trình duyệt sẽ mở để xác thực Google

</details>

<details>
<summary>📘 Facebook Upload</summary>

1. Vào [developers.facebook.com](https://developers.facebook.com) → Create App
2. Thêm product **Pages API**
3. Lấy **Long-lived Page Access Token** (90 ngày)
4. Điền vào `.env`:
   ```
   FACEBOOK_PAGE_ID=123456789
   FACEBOOK_ACCESS_TOKEN=EAAxxxxxxx
   ```

</details>

---

## 🏗️ Kiến Trúc

```
vietdub-auto/
├── backend/
│   ├── main.py                    # CLI entry point
│   ├── api/server.py              # FastAPI + WebSocket server
│   ├── pipeline/
│   │   ├── downloader.py          # yt-dlp + VTT parser
│   │   ├── transcriber.py         # Groq Whisper API
│   │   ├── translator.py          # Gemini + Google Translate
│   │   ├── tts_engine.py          # Edge-TTS vi-VN
│   │   └── audio_mixer.py         # FFmpeg audio processing
│   └── uploaders/
│       ├── youtube_uploader.py    # YouTube Data API v3
│       └── facebook_uploader.py   # Facebook Graph API
├── frontend/
│   └── index.html                 # Web UI (vanilla JS)
├── tests/                         # Unit tests
├── .github/
│   ├── workflows/                 # CI/CD GitHub Actions
│   └── ISSUE_TEMPLATE/           # Bug/Feature templates
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🗺️ Roadmap

- [x] Core pipeline (download → translate → TTS → mix)
- [x] Web UI với realtime progress
- [x] YouTube + Facebook upload
- [x] Docker support
- [ ] Batch processing nhiều URL cùng lúc
- [ ] Voice cloning — giữ giọng diễn viên gốc
- [ ] Auto-generate thumbnail tiếng Việt
- [ ] Telegram Bot interface
- [ ] SaaS hosted version (vietdub.io)

---

## 🤝 Đóng Góp

Mọi đóng góp đều được chào đón! 

```bash
# Fork repo → Clone về
git clone https://github.com/YOUR_USERNAME/vietdub-auto.git

# Tạo branch mới
git checkout -b feature/ten-tinh-nang

# Commit theo convention
git commit -m "feat: thêm tính năng voice cloning"

# Push và tạo Pull Request
git push origin feature/ten-tinh-nang
```

**Commit convention:** `feat:` | `fix:` | `docs:` | `refactor:` | `test:`

---

## ⚠️ Lưu Ý Pháp Lý

> Project này dành cho mục đích học tập và xử lý **nội dung bạn có quyền sử dụng**.
> - Chỉ dùng với video Creative Commons hoặc video của chính bạn
> - Không dùng để vi phạm bản quyền
> - Người dùng tự chịu trách nhiệm về nội dung xử lý

---

## 📄 License

[MIT License](LICENSE) — Free to use, modify, and distribute.

---

<div align="center">

Made with ❤️ in Vietnam 🇻🇳

⭐ **Nếu project hữu ích, cho mình 1 star nhé!** ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=YOUR_USERNAME/vietdub-auto&type=Date)](https://star-history.com/#YOUR_USERNAME/vietdub-auto&Date)

</div>
#   f o d e c u c k  
 
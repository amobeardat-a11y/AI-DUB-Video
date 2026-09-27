<div align="center">

<img src="https://raw.githubusercontent.com/YOUR_USERNAME/vietdub-auto/main/docs/logo.png" alt="VietDub Auto" width="120" />

# 🎬 VietDub Auto

**Tự động lồng tiếng Việt cho video YouTube / Douyin / Bilibili trong vài phút**

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

> Paste link video → Video lồng tiếng Việt xuất hiện trong vài phút

```
Input:  https://www.douyin.com/video/xxxxxxxxxx  (tiếng Trung)
           ↓  xử lý
Output: output/vietdub_video.mp4  🇻🇳
```

**Pipeline tự động:**

```
Video URL (YouTube / Douyin / Bilibili)
    │
    ├─► [1] yt-dlp          → Tải video + subtitle gốc (nếu có)
    │         ↓ (nếu không có sub)
    │   [2] Groq Whisper    → Transcribe audio [zh] → text
    │
    ├─► [3] AI Translate     → Opus → Gemini → Groq → Google (fallback)
    │
    ├─► [4] VieNeu-TTS       → Giọng đọc tiếng Việt (fallback Edge-TTS)
    │
    ├─► [5] FFmpeg          → Mix audio, giữ nhạc nền
    │
    └─► [6] YouTube / FB API → Auto upload (tùy chọn)
```

---

## ✨ Tính Năng

| Tính năng | Mô tả |
|---|---|
| � **Đa nền tảng** | Tải từ YouTube, Douyin, Bilibili... (bất kỳ site nào yt-dlp hỗ trợ) |
| 🎯 **Smart subtitle** | Ưu tiên subtitle gốc (zh/en/vi), fallback Groq Whisper ép ngôn ngữ nguồn |
| 🧠 **AI Translation** | Chuỗi fallback Opus → Gemini → Groq → Google, dịch tự nhiên theo ngữ cảnh |
| 🔊 **TTS chất lượng cao** | VieNeu-TTS (neural on-device) làm chính, Edge-TTS fallback |
| 🎚️ **Smart audio mix** | Giữ nhạc nền gốc, TTS rõ ràng |
| ⚡ **Tempo adjustment** | FFmpeg tự điều chỉnh tốc độ đọc khớp timestamp |
| 📺 **Auto upload** | YouTube Data API v3 + Facebook Graph API |
| ☁️ **Chạy đám mây** | GitHub Actions (CPU) hoặc Colab/Kaggle (GPU miễn phí) |
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
# Cơ bản (YouTube / Douyin / Bilibili đều được)
python backend/main.py --url "https://www.douyin.com/video/xxxxxxxxxx"

# Chỉ định giọng VieNeu
python backend/main.py --url "..." --voice "Hải Đăng"

# Auto upload sau khi xử lý
python backend/main.py --url "..." --upload-youtube --upload-facebook

# Chỉ định thư mục output
python backend/main.py --url "..." --output ./my_videos

# Debug (giữ temp files)
python backend/main.py --url "..." --keep-temp
```

### Video tiếng Trung (Douyin / Bilibili)

Video thường **không có sẵn phụ đề** → pipeline tự động dùng **Groq Whisper** ép ngôn ngữ nguồn để transcribe. Đặt biến môi trường:

```env
SOURCE_LANG=zh   # nguồn tiếng Trung (mặc định)
```

Nếu site chặn tải / giới hạn chất lượng, export cookies (định dạng Netscape) và trỏ `YT_COOKIES_FILE`:

```env
YT_COOKIES_FILE=/path/to/cookies.txt
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

## ☁️ Chạy Trên Đám Mây (Miễn Phí)

### Colab / Kaggle (có GPU — khuyến nghị cho VieNeu-TTS)

Dùng notebook `notebooks/vietdub_colab_kaggle.ipynb` (chạy được cả Colab lẫn Kaggle):

1. Bật GPU: Colab → `Runtime` → `T4 GPU`; Kaggle → `Accelerator` → `GPU T4 x2` / `P100`.
2. Chạy lần lượt các cell: check GPU → clone repo → cài deps + VieNeu → điền API keys → dán URL → chạy → tải kết quả.
3. Có cell tùy chọn upload cookies cho Douyin/Bilibili.

| Nền tảng | GPU | Giới hạn | Hợp cho |
|---|---|---|---|
| **Colab** | T4 free | ~90 phút không tương tác bị ngắt, tối đa ~12h | Dub lẻ từng video |
| **Kaggle** | T4 x2 / P100 | 30h GPU/tuần, session tối đa 12h | Batch nhiều video, ổn định hơn |

### GitHub Actions (không GPU — hợp Edge-TTS)

Workflow `.github/workflows/dub.yml` chạy thủ công qua `workflow_dispatch`:

1. Vào tab **Actions** → chọn workflow → **Run workflow**.
2. Nhập `url`, chọn `tts_engine`, bật/tắt upload.
3. Kết quả (mp4 + srt) lưu ở **Artifacts** (7 ngày).

> ⚠️ Actions **không có GPU** → VieNeu chạy CPU rất chậm. Nên chọn `tts_engine=edge` trên Actions, hoặc dùng Colab/Kaggle cho VieNeu.

Cấu hình secrets cần thiết trong **Settings → Secrets and variables → Actions**: `OPUS_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`, `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN`, `YT_COOKIES` (tùy chọn).

---

## ⚙️ Cấu Hình

Tất cả cấu hình trong file `.env` (xem `.env.example`):

```env
# === Nguồn ===
SOURCE_LANG=zh                    # ngôn ngữ video gốc (zh cho tiếng Trung)

# === Dịch (điền ít nhất 1) ===
OPUS_API_KEY=your_key             # Claude Opus (ưu tiên cao nhất)
OPUS_API_URL=https://api.justwoker.icu/v1/messages
OPUS_MODEL=claude-opus-4-8
GEMINI_API_KEY=your_key           # https://aistudio.google.com
GROQ_API_KEY=your_key             # dịch + Whisper transcribe
GROQ_TRANSLATE_MODEL=llama-3.3-70b-versatile

# === TTS ===
TTS_ENGINE=vieneu                 # vieneu (chính) | edge (fallback)
VIENEU_VOICE=Hải Đăng
EDGE_FALLBACK_VOICE=vi-VN-HoaiMyNeural

# === Video ===
ORIGINAL_AUDIO_VOLUME=0.12        # 12% âm gốc giữ lại
VIDEO_QUALITY=720                 # 480 | 720 | 1080

# === Tải ===
YT_COOKIES_FILE=                  # cookies.txt cho Douyin/Bilibili/YouTube

# === Upload YouTube (tùy chọn) ===
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=

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
│   │   ├── downloader.py          # yt-dlp đa nền tảng + VTT parser
│   │   ├── transcriber.py         # Groq Whisper (ép SOURCE_LANG)
│   │   ├── translator.py          # Opus → Gemini → Groq → Google
│   │   ├── tts_engine.py          # VieNeu-TTS + Edge-TTS fallback
│   │   └── audio_mixer.py         # FFmpeg audio processing
│   └── uploaders/
│       ├── youtube_uploader.py    # YouTube Data API v3
│       └── facebook_uploader.py   # Facebook Graph API
├── frontend/
│   └── index.html                 # Web UI (vanilla JS)
├── notebooks/
│   └── vietdub_colab_kaggle.ipynb # Chạy trên Colab/Kaggle (GPU free)
├── tests/                         # Unit tests
├── .github/
│   └── workflows/dub.yml          # GitHub Actions (workflow_dispatch)
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
#   f o d e c u c k 
 
 
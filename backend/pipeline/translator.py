"""
translator.py — Dịch subtitle sang tiếng Việt
Ưu tiên fallback: Opus (claude-opus-4-8) → Gemini → Groq (stream) → Google Translate
"""
import os
import time
import requests
from typing import Optional
from .downloader import SubtitleEntry


OPUS_API_URL = os.getenv("OPUS_API_URL", "https://api.justwoker.icu/v1/messages")
OPUS_MODEL = os.getenv("OPUS_MODEL", "claude-opus-4-8")
GROQ_TRANSLATE_MODEL = os.getenv("GROQ_TRANSLATE_MODEL", "llama-3.3-70b-versatile")


# ========== Prompt & Parse dùng chung ==========

def _build_prompt(texts: list[str], context: str = "") -> str:
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
    ctx = f"Ngữ cảnh video: {context}\n" if context else ""
    return (
        "Dịch các câu sau sang tiếng Việt tự nhiên, giữ nguyên phong cách nói "
        "chuyện và cảm xúc.\nChỉ trả về bản dịch theo đúng định dạng số thứ tự "
        f"tương ứng. Không thêm giải thích.\n{ctx}\n{numbered}"
    )


def _parse_numbered(raw: str, expected: int) -> list[str]:
    results = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if line and line[0].isdigit():
            dot_idx = line.find(". ")
            if dot_idx != -1:
                results.append(line[dot_idx + 2:].strip())
    if len(results) != expected:
        raise ValueError(f"Parse thất bại ({len(results)}/{expected} dòng)")
    return results


# ========== Opus (Anthropic messages API) ==========

def _translate_batch_opus(texts: list[str], context: str = "") -> list[str]:
    """Dịch batch bằng claude-opus-4-8 qua messages API (SSE stream để né Cloudflare 524)."""
    import json as _json

    api_key = os.getenv("OPUS_API_KEY")
    if not api_key:
        raise ValueError("OPUS_API_KEY chưa được set")

    resp = requests.post(
        OPUS_API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "accept": "text/event-stream",
        },
        json={
            "model": OPUS_MODEL,
            "max_tokens": 16000,
            "stream": True,
            "messages": [{"role": "user", "content": _build_prompt(texts, context)}],
        },
        timeout=120,
        stream=True,
    )
    resp.raise_for_status()

    parts = []
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break
        try:
            evt = _json.loads(payload)
        except ValueError:
            continue
        if evt.get("type") == "content_block_delta":
            delta = evt.get("delta", {})
            if delta.get("type") == "text_delta":
                parts.append(delta.get("text", ""))

    raw = "".join(parts).strip()
    return _parse_numbered(raw, len(texts))


# ========== Gemini Translator ==========

def _translate_batch_gemini(texts: list[str], context: str = "") -> list[str]:
    """Dịch batch text bằng Gemini API."""
    import google.generativeai as genai
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY chưa được set")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(_build_prompt(texts, context))
    return _parse_numbered(response.text, len(texts))


# ========== Groq (streaming) ==========

def _translate_batch_groq(texts: list[str], context: str = "") -> list[str]:
    """Dịch batch bằng Groq LLM, gọi kiểu stream."""
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY chưa được set")

    client = Groq(api_key=api_key)
    stream = client.chat.completions.create(
        model=GROQ_TRANSLATE_MODEL,
        messages=[{"role": "user", "content": _build_prompt(texts, context)}],
        stream=True,
    )
    raw = "".join(
        chunk.choices[0].delta.content or ""
        for chunk in stream
        if chunk.choices
    )
    return _parse_numbered(raw, len(texts))


def _translate_single_google(text: str, target_lang: str = "vi") -> str:
    """Google Translate không cần API key (scraping unofficial endpoint)."""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": target_lang,
            "dt": "t",
            "q": text,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        translated = "".join(item[0] for item in data[0] if item[0])
        return translated
    except Exception as e:
        print(f"⚠️  Google Translate lỗi: {e}")
        return text


# ========== Main Translate Function ==========

def translate_subtitles(
    subtitles: list[SubtitleEntry],
    video_title: str = "",
    batch_size: int = 20,
) -> list[SubtitleEntry]:
    """
    Dịch toàn bộ subtitle sang tiếng Việt.
    Fallback: Opus → Gemini → Groq (stream) → Google Translate từng câu.
    """
    if not subtitles:
        return []

    print(f"🌐 Bắt đầu dịch {len(subtitles)} subtitle entries...")

    # Chuỗi engine batch theo thứ tự ưu tiên, chỉ bật engine có API key
    engines = []
    if os.getenv("OPUS_API_KEY"):
        engines.append(("Opus", _translate_batch_opus))
    if os.getenv("GEMINI_API_KEY"):
        engines.append(("Gemini", _translate_batch_gemini))
    if os.getenv("GROQ_API_KEY"):
        engines.append(("Groq", _translate_batch_groq))

    translated_entries = []

    # Chia batch để tránh rate limit
    for batch_start in range(0, len(subtitles), batch_size):
        batch = subtitles[batch_start:batch_start + batch_size]
        batch_texts = [entry.text for entry in batch]
        
        batch_idx = batch_start // batch_size + 1
        total_batches = (len(subtitles) + batch_size - 1) // batch_size
        print(f"  📦 Batch {batch_idx}/{total_batches} ({len(batch)} entries)...")
        
        translated_texts = None

        # Thử lần lượt các engine batch theo ưu tiên
        for name, fn in engines:
            try:
                translated_texts = fn(batch_texts, video_title)
                break
            except Exception as e:
                print(f"  ⚠️  {name} lỗi: {e}. Thử engine tiếp theo...")
                translated_texts = None

        # Fallback cuối: Google Translate từng câu
        if translated_texts is None:
            print("  ⚠️  Tất cả LLM lỗi. Chuyển sang Google Translate...")
            translated_texts = []
            for text in batch_texts:
                vi_text = _translate_single_google(text)
                translated_texts.append(vi_text)
                time.sleep(0.2)  # tránh rate limit
        
        # Ghép lại với timestamp gốc
        for entry, vi_text in zip(batch, translated_texts):
            translated_entries.append(SubtitleEntry(
                start=entry.start,
                end=entry.end,
                text=vi_text,
            ))
        
        # Nghỉ giữa các batch LLM để tránh rate limit
        if engines and batch_start + batch_size < len(subtitles):
            time.sleep(1)
    
    print(f"✅ Dịch xong {len(translated_entries)} entries")
    return translated_entries


def export_srt(subtitles: list[SubtitleEntry], output_path: str):
    """Xuất subtitle ra file .srt."""
    def fmt_time(secs: float) -> str:
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        s = int(secs % 60)
        ms = int((secs - int(secs)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    
    with open(output_path, "w", encoding="utf-8") as f:
        for i, entry in enumerate(subtitles, 1):
            f.write(f"{i}\n")
            f.write(f"{fmt_time(entry.start)} --> {fmt_time(entry.end)}\n")
            f.write(f"{entry.text}\n\n")
    
    print(f"📝 Exported SRT: {output_path}")

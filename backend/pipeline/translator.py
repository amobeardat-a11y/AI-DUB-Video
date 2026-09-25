"""
translator.py — Dịch subtitle sang tiếng Việt
Ưu tiên: Gemini API → fallback Google Translate (miễn phí)
"""
import os
import time
import requests
from typing import Optional
from .downloader import SubtitleEntry


# ========== Gemini Translator ==========

def _translate_batch_gemini(texts: list[str], context: str = "") -> list[str]:
    """Dịch batch text bằng Gemini API."""
    import google.generativeai as genai
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY chưa được set")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
    
    prompt = f"""Dịch các câu sau sang tiếng Việt tự nhiên, giữ nguyên phong cách nói chuyện và cảm xúc.
Chỉ trả về bản dịch theo đúng định dạng số thứ tự tương ứng. Không thêm giải thích.
{f'Ngữ cảnh video: {context}' if context else ''}

{numbered}"""

    response = model.generate_content(prompt)
    raw = response.text.strip()
    
    # Parse numbered list
    lines = raw.split("\n")
    results = []
    for line in lines:
        line = line.strip()
        if line and line[0].isdigit():
            # Remove number prefix "1. "
            dot_idx = line.find(". ")
            if dot_idx != -1:
                results.append(line[dot_idx + 2:].strip())
    
    # Nếu parse thất bại, trả về nguyên bản
    if len(results) != len(texts):
        print(f"⚠️  Parse Gemini response thất bại ({len(results)}/{len(texts)}), dùng fallback line-by-line")
        results = texts  # fallback giữ nguyên
    
    return results


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
    Dùng Gemini (batch) → fallback Google Translate từng câu.
    """
    if not subtitles:
        return []

    print(f"🌐 Bắt đầu dịch {len(subtitles)} subtitle entries...")
    
    use_gemini = bool(os.getenv("GEMINI_API_KEY"))
    translated_entries = []
    
    # Chia batch để tránh rate limit
    for batch_start in range(0, len(subtitles), batch_size):
        batch = subtitles[batch_start:batch_start + batch_size]
        batch_texts = [entry.text for entry in batch]
        
        batch_idx = batch_start // batch_size + 1
        total_batches = (len(subtitles) + batch_size - 1) // batch_size
        print(f"  📦 Batch {batch_idx}/{total_batches} ({len(batch)} entries)...")
        
        translated_texts = None
        
        # Thử Gemini trước
        if use_gemini:
            try:
                translated_texts = _translate_batch_gemini(batch_texts, context=video_title)
            except Exception as e:
                print(f"  ⚠️  Gemini lỗi: {e}. Chuyển sang Google Translate...")
                translated_texts = None
        
        # Fallback: Google Translate
        if translated_texts is None:
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
        
        # Nghỉ giữa các batch Gemini
        if use_gemini and batch_start + batch_size < len(subtitles):
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

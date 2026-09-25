"""
facebook_uploader.py — Upload video lên Facebook Page bằng Graph API
Cần: Page Access Token (long-lived)
"""
import os
import time
import requests


FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "")
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
GRAPH_API_URL = "https://graph.facebook.com/v19.0"


def upload_to_facebook(
    video_path: str,
    title: str,
    description: str = "",
    published: bool = False,  # False = save as draft
) -> str:
    """
    Upload video lên Facebook Page.
    Dùng resumable upload cho video lớn.
    
    Returns:
        Facebook video ID
    """
    page_id = FACEBOOK_PAGE_ID
    token = FACEBOOK_ACCESS_TOKEN
    
    if not page_id or not token:
        raise ValueError("Cần set FACEBOOK_PAGE_ID và FACEBOOK_ACCESS_TOKEN trong .env")
    
    print(f"📘 Đang upload lên Facebook: {title}")
    
    video_size = os.path.getsize(video_path)
    print(f"   File size: {video_size / 1024 / 1024:.1f} MB")
    
    # === Bước 1: Khởi tạo upload session ===
    init_resp = requests.post(
        f"{GRAPH_API_URL}/{page_id}/videos",
        data={
            "upload_phase": "start",
            "file_size": video_size,
            "access_token": token,
        }
    )
    init_resp.raise_for_status()
    init_data = init_resp.json()
    
    upload_session_id = init_data.get("upload_session_id")
    video_id = init_data.get("video_id")
    start_offset = int(init_data.get("start_offset", 0))
    end_offset = int(init_data.get("end_offset", video_size))
    
    print(f"   Upload session: {upload_session_id}")
    
    # === Bước 2: Upload chunks ===
    with open(video_path, "rb") as f:
        while start_offset < video_size:
            f.seek(start_offset)
            chunk = f.read(end_offset - start_offset)
            
            chunk_resp = requests.post(
                f"{GRAPH_API_URL}/{page_id}/videos",
                data={
                    "upload_phase": "transfer",
                    "upload_session_id": upload_session_id,
                    "start_offset": start_offset,
                    "access_token": token,
                },
                files={"video_file_chunk": chunk},
            )
            chunk_resp.raise_for_status()
            chunk_data = chunk_resp.json()
            
            start_offset = int(chunk_data.get("start_offset", video_size))
            end_offset = int(chunk_data.get("end_offset", video_size))
            
            progress = min(start_offset / video_size * 100, 100)
            print(f"  ⬆️  Upload: {progress:.0f}%")
    
    # === Bước 3: Finalize ===
    finish_resp = requests.post(
        f"{GRAPH_API_URL}/{page_id}/videos",
        data={
            "upload_phase": "finish",
            "upload_session_id": upload_session_id,
            "title": f"[VietDub] {title}",
            "description": description or f"Video lồng tiếng Việt tự động\n{title}",
            "published": "true" if published else "false",
            "access_token": token,
        }
    )
    finish_resp.raise_for_status()
    
    fb_url = f"https://facebook.com/{video_id}"
    print(f"✅ Facebook upload thành công: {fb_url}")
    return video_id

"""
youtube_uploader.py — Upload video lên YouTube bằng YouTube Data API v3
Cần: OAuth 2.0 credentials (client_secrets.json)
"""
import os
import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CREDENTIALS_FILE = os.getenv("YOUTUBE_CREDENTIALS_FILE", "youtube_credentials.json")
CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")


def _creds_from_env():
    """Tạo credentials từ env (headless — cho GitHub Actions/CI)."""
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")
    if not (client_id and client_secret and refresh_token):
        return None
    from google.oauth2.credentials import Credentials
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def get_youtube_service():
    """Lấy authenticated YouTube service."""
    # Ưu tiên refresh token từ env (headless, chạy được trên GitHub Actions)
    creds = _creds_from_env()
    if creds:
        return build("youtube", "v3", credentials=creds)

    creds_path = Path(CREDENTIALS_FILE)
    if creds_path.exists():
        with open(creds_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(creds_path, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(
    video_path: str,
    title: str,
    description: str = "",
    tags: list[str] = None,
    category_id: str = "22",  # 22 = People & Blogs
    privacy: str = "private",  # private, unlisted, public
) -> str:
    """
    Upload video lên YouTube.
    
    Returns:
        YouTube video ID
    """
    print(f"📺 Đang upload lên YouTube: {title}")
    
    youtube = get_youtube_service()
    
    body = {
        "snippet": {
            "title": f"[VietDub] {title}",
            "description": description or f"Video lồng tiếng Việt tự động\n\nOriginal: {title}",
            "tags": tags or ["vietdub", "tiếng việt", "lồng tiếng"],
            "categoryId": category_id,
            "defaultLanguage": "vi",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    
    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 10,  # 10MB chunks
    )
    
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            print(f"  ⬆️  Upload: {progress}%")
    
    video_id = response.get("id", "")
    url = f"https://youtube.com/watch?v={video_id}"
    print(f"✅ YouTube upload thành công: {url}")
    return video_id

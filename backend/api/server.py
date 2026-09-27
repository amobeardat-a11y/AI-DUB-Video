"""
api/server.py — FastAPI backend với WebSocket progress tracking
"""
import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

app = FastAPI(title="VietDub Auto API", version="1.0.0")

# Cấu hình CORS origins qua env (mặc định cho local dev). Không dùng "*" kèm credentials.
_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost,http://localhost:80,http://localhost:8000,http://127.0.0.1",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (dùng Redis trong production)
jobs: dict[str, dict] = {}
job_websockets: dict[str, list[WebSocket]] = {}


class JobRequest(BaseModel):
    url: str
    voice: Optional[str] = "vi-VN-HoaiMyNeural"
    upload_youtube: bool = False
    upload_facebook: bool = False


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, running, done, error
    progress: int  # 0-100
    step: str
    output_video: Optional[str] = None
    youtube_url: Optional[str] = None
    facebook_url: Optional[str] = None
    error: Optional[str] = None


async def broadcast_progress(job_id: str, step: str, progress: int, extra: dict = None):
    """Gửi progress update qua WebSocket."""
    jobs[job_id].update({
        "step": step,
        "progress": progress,
        **(extra or {})
    })
    
    if job_id in job_websockets:
        dead = []
        for ws in job_websockets[job_id]:
            try:
                await ws.send_json({
                    "job_id": job_id,
                    "step": step,
                    "progress": progress,
                    "status": jobs[job_id]["status"],
                    **(extra or {}),
                })
            except Exception:
                dead.append(ws)
        for ws in dead:
            job_websockets[job_id].remove(ws)


async def process_video(job_id: str, request: JobRequest):
    """Background task xử lý video."""
    output_dir = Path("./output") / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    jobs[job_id]["status"] = "running"
    
    try:
        # Import pipeline
        from pipeline.downloader import download_video
        from pipeline.transcriber import transcribe_with_groq
        from pipeline.translator import translate_subtitles, export_srt
        from pipeline.tts_engine import generate_all_segments
        from pipeline.audio_mixer import mix_audio_to_video
        
        # Step 1: Download
        await broadcast_progress(job_id, "Đang tải video YouTube...", 5)
        result = await asyncio.to_thread(download_video, request.url, str(output_dir))
        
        # Step 2: Transcribe
        subtitles = result.subtitles
        if result.source == "whisper_pending":
            await broadcast_progress(job_id, "Đang transcribe bằng Groq Whisper...", 20)
            subtitles = await asyncio.to_thread(transcribe_with_groq, result.audio_path)
        else:
            await broadcast_progress(job_id, f"Tìm thấy subtitle YouTube ({result.source})", 20)
        
        # Step 3: Translate
        await broadcast_progress(job_id, f"Đang dịch {len(subtitles)} câu sang tiếng Việt...", 35)
        vi_subs = await asyncio.to_thread(
            translate_subtitles, subtitles, result.title
        )
        srt_path = str(output_dir / "vi.srt")
        export_srt(vi_subs, srt_path)
        
        # Step 4: TTS
        await broadcast_progress(job_id, "Đang tạo giọng nói tiếng Việt (Edge-TTS)...", 55)
        segments_dir = str(output_dir / "segments")
        tts_segments = await asyncio.to_thread(
            generate_all_segments, vi_subs, segments_dir, request.voice
        )
        
        # Step 5: Mix
        await broadcast_progress(job_id, "Đang ghép audio vào video (FFmpeg)...", 75)
        safe_title = "".join(c for c in result.title if c.isalnum() or c in " -_")[:40]
        out_video = str(output_dir / f"vietdub_{safe_title}.mp4")
        
        await asyncio.to_thread(
            mix_audio_to_video,
            result.video_path,
            tts_segments,
            out_video,
            temp_dir=str(output_dir / "temp"),
        )
        
        jobs[job_id]["output_video"] = out_video
        jobs[job_id]["title"] = result.title
        
        # Step 6: Upload
        yt_url = None
        fb_url = None
        
        if request.upload_youtube:
            await broadcast_progress(job_id, "Đang upload lên YouTube...", 88)
            try:
                from uploaders.youtube_uploader import upload_to_youtube
                yt_id = await asyncio.to_thread(
                    upload_to_youtube, out_video, result.title, privacy="private"
                )
                yt_url = f"https://youtube.com/watch?v={yt_id}"
                jobs[job_id]["youtube_url"] = yt_url
            except Exception as e:
                await broadcast_progress(job_id, f"YouTube upload thất bại: {e}", 88)
        
        if request.upload_facebook:
            await broadcast_progress(job_id, "Đang upload lên Facebook...", 94)
            try:
                from uploaders.facebook_uploader import upload_to_facebook
                fb_id = await asyncio.to_thread(
                    upload_to_facebook, out_video, result.title
                )
                fb_url = f"https://facebook.com/{fb_id}"
                jobs[job_id]["facebook_url"] = fb_url
            except Exception as e:
                await broadcast_progress(job_id, f"Facebook upload thất bại: {e}", 94)
        
        # Done
        jobs[job_id]["status"] = "done"
        await broadcast_progress(job_id, "✅ Hoàn thành!", 100, {
            "output_video": f"/download/{job_id}",
            "youtube_url": yt_url,
            "facebook_url": fb_url,
        })
    
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        await broadcast_progress(job_id, f"❌ Lỗi: {str(e)}", 0, {"error": str(e)})
        raise


@app.post("/api/jobs", response_model=JobStatus)
async def create_job(request: JobRequest, background_tasks: BackgroundTasks):
    """Tạo job xử lý video mới."""
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "pending",
        "step": "Đang khởi tạo...",
        "progress": 0,
        "url": request.url,
    }
    background_tasks.add_task(process_video, job_id, request)
    return JobStatus(job_id=job_id, status="pending", progress=0, step="Đang khởi tạo...")


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    """Lấy trạng thái job."""
    if job_id not in jobs:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    
    job = jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job.get("status", "pending"),
        progress=job.get("progress", 0),
        step=job.get("step", ""),
        output_video=f"/download/{job_id}" if job.get("output_video") else None,
        youtube_url=job.get("youtube_url"),
        facebook_url=job.get("facebook_url"),
        error=job.get("error"),
    )


@app.websocket("/ws/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """WebSocket để nhận progress realtime."""
    await websocket.accept()
    
    if job_id not in job_websockets:
        job_websockets[job_id] = []
    job_websockets[job_id].append(websocket)
    
    try:
        # Gửi trạng thái hiện tại ngay lập tức
        if job_id in jobs:
            job = jobs[job_id]
            await websocket.send_json({
                "job_id": job_id,
                "step": job.get("step", ""),
                "progress": job.get("progress", 0),
                "status": job.get("status", "pending"),
            })
        
        while True:
            await websocket.receive_text()  # Keep alive
    except WebSocketDisconnect:
        if job_id in job_websockets:
            try:
                job_websockets[job_id].remove(websocket)
            except ValueError:
                pass


@app.get("/download/{job_id}")
async def download_video_file(job_id: str):
    """Download video đã xử lý."""
    if job_id not in jobs or not jobs[job_id].get("output_video"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Video chưa sẵn sàng")
    
    video_path = jobs[job_id]["output_video"]
    title = jobs[job_id].get("title", "vietdub")
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:40]
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"VietDub_{safe_title}.mp4",
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

import os
import tempfile
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Header, Query
from pydantic import BaseModel

from instagrapi import Client
from instagrapi.exceptions import LoginRequired

logger = logging.getLogger("igpost.api")

app = FastAPI(title="igpost API", version="0.1.0")


class UploadRequest(BaseModel):
    video: str
    description: str


def try_login_with_session_then_password(
    client: Client, 
    username: Optional[str], 
    password: Optional[str], 
    session_id: Optional[str],
    session_file: str
) -> None:
    """Login using session_id first, then username/password if needed."""
    client.delay_range = [1, 3]

    # Try session_id first if provided
    if session_id:
        try:
            logger.info("Attempting login with session_id")
            client.login_by_sessionid(session_id)
            # Validate session
            try:
                client.get_timeline_feed()
                logger.info("Authenticated via session_id")
                return
            except LoginRequired:
                logger.info("Session_id invalid, falling back to username/password")
        except Exception as e:
            logger.info("Session_id login failed: %s", e)

    # Try username/password
    if not username or not password:
        raise ValueError("Either session_id or username/password must be provided")
    
    logger.info("Attempting username/password login")
    client.set_settings({})
    try:
        client.set_uuids({})
    except Exception:
        pass
    client.login(username, password)
    logger.info("Authenticated via username/password")

    # Persist session for future use
    try:
        client.dump_settings(session_file)
        logger.info("Session saved to %s", session_file)
    except Exception as e:
        logger.info("Failed to save session: %s", e)


def upload_video(client: Client, video_path: str, caption: str) -> str:
    logger.info("Uploading video: %s", video_path)
    media = client.clip_upload(video_path, caption)
    media_code = getattr(media, "code", None)
    if media_code:
        url = f"https://www.instagram.com/p/{media_code}/"
        logger.info("Upload succeeded: %s", url)
        return url
    logger.info("Upload completed without code")
    return ""


def get_authenticated_client(
    username: Optional[str] = None,
    password: Optional[str] = None, 
    session_id: Optional[str] = None,
    session_file: str = "session.json"
) -> Client:
    client = Client()
    try_login_with_session_then_password(
        client,
        username=username,
        password=password,
        session_id=session_id,
        session_file=session_file,
    )
    return client


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/profile")
async def profile(
    username: Optional[str] = None,
    password: Optional[str] = None,
    session_id: Optional[str] = None,
    session_file: str = "session.json"
) -> dict:
    try:
        client = get_authenticated_client(username, password, session_id, session_file)
        info = client.account_info()
        # Pydantic v2 safe serialization
        try:
            return info.model_dump()  # type: ignore[attr-defined]
        except Exception:
            return info.dict()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/upload")
async def upload(
    video: Optional[UploadFile] = File(None),
    video_path: Optional[str] = Form(None),
    description: str = Form(...),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    session_file: str = Form("session.json")
) -> dict:
    try:
        # Determine video source: uploaded file or file path
        if video and video_path:
            raise HTTPException(status_code=400, detail="Provide either video file or video_path, not both")
        
        if not video and not video_path:
            raise HTTPException(status_code=400, detail="Provide either video file or video_path")
        
        if video:
            # Save uploaded file to temp location
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                content = await video.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name
            cleanup_temp = True
        else:
            # Use provided file path
            if not os.path.isfile(video_path):
                raise HTTPException(status_code=400, detail=f"Video file not found: {video_path}")
            tmp_path = video_path
            cleanup_temp = False
        
        try:
            client = get_authenticated_client(username, password, session_id, session_file)
            url = upload_video(client, tmp_path, description)
            return {"url": url or "", "status": "ok"}
        finally:
            # Clean up temp file only if we created it
            if cleanup_temp:
                os.unlink(tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.on_event("startup")
async def on_startup() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    logger.info("API starting up")

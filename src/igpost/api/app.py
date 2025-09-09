import os
import tempfile
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from instagrapi import Client

from igpost.cli import (
    try_login_with_session_then_password,
    upload_video,
    load_env_credentials,
    configure_logging,
)

logger = logging.getLogger("igpost.api")

app = FastAPI(title="igpost API", version="0.1.0")


class UploadRequest(BaseModel):
    video: str
    description: str


def resolve_credentials() -> tuple[Optional[str], Optional[str]]:
    # Priority: .env -> IG_* env vars -> None (API does not accept plaintext payload creds by design)
    username, password = load_env_credentials()
    if username and password:
        logger.info("Using credentials from .env file")
        return username, password

    username = os.getenv("IG_USERNAME")
    password = os.getenv("IG_PASSWORD")
    if username and password:
        logger.info("Using credentials from system environment variables")
        return username, password

    return None, None


def get_session_file() -> str:
    return os.getenv("IGPOST_SESSION_FILE", "session.json")


def get_authenticated_client() -> Client:
    client = Client()
    username, password = resolve_credentials()
    try_login_with_session_then_password(
        client,
        username=username,
        password=password,
        session_file=get_session_file(),
    )
    return client


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/profile")
async def profile() -> dict:
    try:
        client = get_authenticated_client()
        info = client.account_info()
        # Pydantic v2 safe serialization
        try:
            return info.model_dump()  # type: ignore[attr-defined]
        except Exception:
            return info.dict()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/upload")
async def upload(req: UploadRequest) -> dict:
    video_path = req.video
    caption = req.description
    if not os.path.isfile(video_path):
        raise HTTPException(status_code=400, detail=f"Video not found: {video_path}")
    try:
        client = get_authenticated_client()
        url = upload_video(client, video_path, caption)
        return {"url": url or "", "status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.on_event("startup")
async def on_startup() -> None:
    verbose = os.getenv("IGPOST_VERBOSE", "false").lower() in {"1", "true", "yes"}
    configure_logging(verbose)
    logger.info("API starting up")

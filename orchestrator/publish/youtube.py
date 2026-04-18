from __future__ import annotations
import os
import pickle
from dataclasses import dataclass, field
from typing import Optional
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = os.path.expanduser("~/.config/pixelle/youtube_token.pickle")
CLIENT_SECRETS_PATH = os.path.expanduser("~/.config/pixelle/youtube_client_secrets.json")


@dataclass
class VideoMeta:
    title: str
    description: str = ""
    tags: list = field(default_factory=list)
    category_id: str = "22"
    privacy: str = "private"
    thumbnail_path: Optional[str] = None


def _get_credentials():
    creds = None
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)
    return creds


async def upload_to_youtube(video_path: str, meta: VideoMeta) -> str:
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _upload_sync, video_path, meta)


def _upload_sync(video_path: str, meta: VideoMeta) -> str:
    creds = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": meta.title,
            "description": meta.description,
            "tags": meta.tags or [],
            "categoryId": meta.category_id,
        },
        "status": {"privacyStatus": meta.privacy},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part=",".join(body.keys()), body=body, media_body=media
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response["id"]

import os
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

router = APIRouter()

# --- Startup Validation ---
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI")
YOUTUBE_SCOPES = os.getenv("YOUTUBE_SCOPES", "https://www.googleapis.com/auth/youtube.upload").split(",")

if not all([YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REDIRECT_URI]):
    missing = [k for k, v in {
        "YOUTUBE_CLIENT_ID": YOUTUBE_CLIENT_ID,
        "YOUTUBE_CLIENT_SECRET": YOUTUBE_CLIENT_SECRET,
        "YOUTUBE_REDIRECT_URI": YOUTUBE_REDIRECT_URI
    }.items() if not v]
    raise ValueError(f"Missing required YouTube environment variables: {', '.join(missing)}")

TOKEN_DIR = Path("tokens")
CLIENT_CONFIG = {
    "web": {
        "client_id": YOUTUBE_CLIENT_ID,
        "client_secret": YOUTUBE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [YOUTUBE_REDIRECT_URI]
    }
}

# --- Schemas ---
class YoutubeUploadRequest(BaseModel):
    video_path: str
    title: str
    description: str
    tags: List[str] = Field(default_factory=list)
    privacy: str = Field(default="private", pattern="^(public|private|unlisted)$")

# --- Internal Helpers ---
def _get_token_path(user_id: str) -> Path:
    return TOKEN_DIR / f"youtube_{user_id}.json"

def _load_token(user_id: str) -> Optional[dict]:
    path = _get_token_path(user_id)
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None

def _save_token(user_id: str, token: dict) -> None:
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    with open(_get_token_path(user_id), "w") as f:
        json.dump(token, f)

def _build_credentials(token_data: dict) -> Credentials:
    return Credentials.from_authorized_user_info(token_data, YOUTUBE_SCOPES)

def _refresh_if_expired(user_id: str, creds: Credentials) -> Credentials:
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleRequest())
            _save_token(user_id, json.loads(creds.to_json()))
        except Exception:
            raise HTTPException(status_code=401, detail="Token expired. Re-authenticate.")
    return creds

# --- Routes ---
@router.get("/auth/{user_id}")
async def get_auth_url(user_id: str):
    """Builds and returns the Google OAuth2 authorization URL for a specific user."""
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=YOUTUBE_SCOPES)
    flow.redirect_uri = YOUTUBE_REDIRECT_URI
    
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=user_id,
        prompt='consent'
    )
    return {"auth_url": auth_url}

@router.get("/callback")
async def youtube_callback(code: str, state: str):
    """Exchanges auth code for tokens and saves them."""
    try:
        flow = Flow.from_client_config(CLIENT_CONFIG, scopes=YOUTUBE_SCOPES)
        flow.redirect_uri = YOUTUBE_REDIRECT_URI
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        _save_token(state, json.loads(credentials.to_json()))
        
        return {"status": "authenticated", "user_id": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@router.post("/upload/{user_id}")
async def upload_video(user_id: str, req: YoutubeUploadRequest):
    """Loads user token, refreshes if needed, and uploads video to YouTube."""
    token_data = _load_token(user_id)
    if not token_data:
        raise HTTPException(status_code=401, detail="User not authenticated. Call /auth first.")
    
    try:
        creds = _build_credentials(token_data)
        creds = _refresh_if_expired(user_id, creds)
        
        youtube = build("youtube", "v3", credentials=creds)
        
        if not os.path.exists(req.video_path):
            raise HTTPException(status_code=400, detail=f"Video file not found at: {req.video_path}")

        body = {
            "snippet": {
                "title": req.title,
                "description": req.description,
                "tags": req.tags,
                "categoryId": "22" # People & Blogs
            },
            "status": {
                "privacyStatus": req.privacy
            }
        }

        media = MediaFileUpload(
            req.video_path,
            mimetype="video/*",
            resumable=True
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%")

        return {
            "status": "uploaded",
            "video_id": response.get("id"),
            "url": f"https://www.youtube.com/watch?v={response.get('id')}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failure: {str(e)}")

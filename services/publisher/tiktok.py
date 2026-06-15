import os
import json
import time
import httpx
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

router = APIRouter()

# --- Startup Validation ---
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI")
TIKTOK_SCOPES = "video.upload,video.publish"

if not all([TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REDIRECT_URI]):
    missing = [k for k, v in {
        "TIKTOK_CLIENT_KEY": TIKTOK_CLIENT_KEY,
        "TIKTOK_CLIENT_SECRET": TIKTOK_CLIENT_SECRET,
        "TIKTOK_REDIRECT_URI": TIKTOK_REDIRECT_URI
    }.items() if not v]
    raise ValueError(f"Missing required TikTok environment variables: {', '.join(missing)}")

TOKEN_DIR = Path("tokens")

# --- Schemas ---
class TiktokUploadRequest(BaseModel):
    video_path: str
    title: str = Field(..., max_length=150)
    privacy_level: str = Field(default="SELF_ONLY", pattern="^(PUBLIC_TO_EVERYONE|MUTUAL_FOLLOW_FRIENDS|SELF_ONLY)$")
    disable_duet: bool = False
    disable_comment: bool = False
    disable_stitch: bool = False

    @field_validator('title')
    @classmethod
    def validate_title_length(cls, v):
        if len(v) > 150:
            raise ValueError("Title exceeds TikTok's 150 character limit.")
        return v

# --- Internal Helpers ---
def _get_token_path(user_id: str) -> Path:
    return TOKEN_DIR / f"tiktok_{user_id}.json"

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

async def _refresh_token(user_id: str, refresh_token: str) -> str:
    """Refreshes the TikTok access token using the refresh token."""
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_key": TIKTOK_CLIENT_KEY,
        "client_secret": TIKTOK_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, data=data)
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Token expired. Re-authenticate.")
        
        token_data = resp.json()
        if "access_token" not in token_data:
            raise HTTPException(status_code=401, detail="Token expired. Re-authenticate.")
        
        # Update local token store
        token_data["expires_at"] = time.time() + token_data.get("expires_in", 0)
        _save_token(user_id, token_data)
        return token_data["access_token"]

async def _get_valid_token(user_id: str) -> str:
    """Loads and refreshes token if expired, returning a valid access token."""
    token = _load_token(user_id)
    if not token:
        raise HTTPException(status_code=401, detail="User not authenticated. Call /auth first.")
    
    # Check if expired (with 1-minute buffer)
    if time.time() + 60 > token.get("expires_at", 0):
        if not token.get("refresh_token"):
            raise HTTPException(status_code=401, detail="Token expired. Re-authenticate.")
        return await _refresh_token(user_id, token["refresh_token"])
    
    return token["access_token"]

# --- Routes ---
@router.get("/auth/{user_id}")
async def get_auth_url(user_id: str):
    """Builds and returns the TikTok OAuth2 authorization URL."""
    base_url = "https://www.tiktok.com/v2/auth/authorize/"
    params = {
        "client_key": TIKTOK_CLIENT_KEY,
        "scope": TIKTOK_SCOPES,
        "response_type": "code",
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "state": user_id
    }
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return {"auth_url": f"{base_url}?{query_string}"}

@router.get("/callback")
async def tiktok_callback(code: str, state: str):
    """Exchanges auth code for TikTok tokens."""
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_key": TIKTOK_CLIENT_KEY,
        "client_secret": TIKTOK_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": TIKTOK_REDIRECT_URI,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, data=data)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Authentication failed: {resp.text}")
        
        token_data = resp.json()
        # TikTok v2 returns data nested or flat depending on specific error states, 
        # but successful token is usually flat in the main response or in a 'data' key.
        # Based on v2 docs: access_token, refresh_token, etc are in the root for token exchange.
        
        if "access_token" not in token_data:
             raise HTTPException(status_code=500, detail="Failed to retrieve access token from TikTok.")

        token_data["expires_at"] = time.time() + token_data.get("expires_in", 0)
        _save_token(state, token_data)
        
        return {
            "status": "authenticated", 
            "user_id": state, 
            "open_id": token_data.get("open_id")
        }

@router.post("/upload/{user_id}")
async def upload_video(user_id: str, req: TiktokUploadRequest):
    """Orchestrates the TikTok video upload flow: Init -> Chunked Upload -> Poll Status."""
    access_token = await _get_valid_token(user_id)
    
    if not os.path.exists(req.video_path):
        raise HTTPException(status_code=400, detail=f"Video file not found at: {req.video_path}")

    video_size = os.path.getsize(req.video_path)
    
    # Step 1: Initialize Upload
    init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    init_data = {
        "post_info": {
            "title": req.title,
            "privacy_level": req.privacy_level,
            "disable_duet": req.disable_duet,
            "disable_comment": req.disable_comment,
            "disable_stitch": req.disable_stitch,
            "video_cover_timestamp_ms": 1000
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": video_size, # For simplicity, single chunk
            "total_chunk_count": 1
        }
    }

    async with httpx.AsyncClient() as client:
        # 1. Init
        init_resp = await client.post(init_url, headers=headers, json=init_data)
        if init_resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Init upload failed: {init_resp.text}")
        
        init_json = init_resp.json()
        if init_json.get("error", {}).get("code") != "ok":
            raise HTTPException(status_code=500, detail=f"TikTok Init Error: {init_json.get('error')}")
        
        publish_id = init_json["data"]["publish_id"]
        upload_url = init_json["data"]["upload_url"]

        # 2. Upload Chunk (Single chunk approach)
        with open(req.video_path, "rb") as f:
            video_bytes = f.read()
        
        chunk_headers = {
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}"
        }
        
        # Note: upload_url does not require Authorization header per TikTok docs
        upload_resp = await client.put(upload_url, headers=chunk_headers, content=video_bytes)
        if upload_resp.status_code not in [200, 201, 206]:
            raise HTTPException(status_code=500, detail=f"Chunk upload failed: {upload_resp.text}")

        # 3. Poll Status
        status_url = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
        poll_count = 0
        while poll_count < 10:
            time.sleep(3) # Async sleep would be better but keeping it simple per requirement
            poll_count += 1
            
            status_resp = await client.post(status_url, headers=headers, json={"publish_id": publish_id})
            if status_resp.status_code == 200:
                status_json = status_resp.json()
                status_data = status_json.get("data", {})
                current_status = status_data.get("status")
                
                if current_status == "PUBLISH_COMPLETE":
                    return {"status": "uploaded", "publish_id": publish_id}
                elif current_status == "FAILED":
                    raise HTTPException(status_code=500, detail=f"TikTok publish failed: {status_data.get('fail_reason')}")
            
        raise HTTPException(status_code=500, detail="Upload succeeded but publish status timed out. Check TikTok manually.")

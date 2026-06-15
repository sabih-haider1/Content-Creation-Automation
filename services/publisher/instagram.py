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
INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID")
INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET")
INSTAGRAM_REDIRECT_URI = os.getenv("INSTAGRAM_REDIRECT_URI")
INSTAGRAM_SCOPES = "instagram_basic,instagram_content_publish,pages_read_engagement"

if not all([INSTAGRAM_APP_ID, INSTAGRAM_APP_SECRET, INSTAGRAM_REDIRECT_URI]):
    missing = [k for k, v in {
        "INSTAGRAM_APP_ID": INSTAGRAM_APP_ID,
        "INSTAGRAM_APP_SECRET": INSTAGRAM_APP_SECRET,
        "INSTAGRAM_REDIRECT_URI": INSTAGRAM_REDIRECT_URI
    }.items() if not v]
    raise ValueError(f"Missing required Instagram environment variables: {', '.join(missing)}")

TOKEN_DIR = Path("tokens")

# --- Schemas ---
class InstagramUploadRequest(BaseModel):
    video_url: str
    caption: str = Field(..., max_length=2200)
    cover_url: Optional[str] = None

    @field_validator('video_url')
    @classmethod
    def validate_video_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("video_url must be a publicly accessible URL. Local file paths are not supported by Meta's API.")
        return v

    @field_validator('caption')
    @classmethod
    def validate_caption_length(cls, v):
        if len(v) > 2200:
            raise ValueError("Caption exceeds Instagram's 2200 character limit.")
        return v

# --- Internal Helpers ---
def _get_token_path(user_id: str) -> Path:
    return TOKEN_DIR / f"instagram_{user_id}.json"

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

def _is_token_expired(token: dict) -> bool:
    """Checks if the 60-day long-lived token has expired."""
    return time.time() > token.get("expires_at", 0)

async def _get_valid_token(user_id: str) -> dict:
    """Loads and validates the Instagram token."""
    token = _load_token(user_id)
    if not token:
        raise HTTPException(status_code=401, detail="User not authenticated. Call /auth first.")
    
    if _is_token_expired(token):
        raise HTTPException(status_code=401, detail="Instagram token expired. Re-authenticate via /auth.")
    
    return token

# --- Routes ---
@router.get("/auth/{user_id}")
async def get_auth_url(user_id: str):
    """Builds and returns the Meta OAuth2 authorization URL."""
    base_url = "https://www.facebook.com/v19.0/dialog/oauth"
    params = {
        "client_id": INSTAGRAM_APP_ID,
        "redirect_uri": INSTAGRAM_REDIRECT_URI,
        "scope": INSTAGRAM_SCOPES,
        "response_type": "code",
        "state": user_id
    }
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return {"auth_url": f"{base_url}?{query_string}"}

@router.get("/callback")
async def instagram_callback(code: str, state: str):
    """Exchanges auth code for short-lived token, upgrades to long-lived, and resolves IG Account ID."""
    async with httpx.AsyncClient() as client:
        # Step 1: Exchange code for short-lived token
        token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
        token_params = {
            "client_id": INSTAGRAM_APP_ID,
            "client_secret": INSTAGRAM_APP_SECRET,
            "redirect_uri": INSTAGRAM_REDIRECT_URI,
            "code": code
        }
        resp = await client.post(token_url, params=token_params)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Short-lived token exchange failed: {resp.text}")
        
        short_lived_token = resp.json().get("access_token")

        # Step 2: Upgrade to long-lived token (60 days)
        upgrade_params = {
            "grant_type": "fb_exchange_token",
            "client_id": INSTAGRAM_APP_ID,
            "client_secret": INSTAGRAM_APP_SECRET,
            "fb_exchange_token": short_lived_token
        }
        resp = await client.get(token_url, params=upgrade_params)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Long-lived token upgrade failed: {resp.text}")
        
        long_lived_data = resp.json()
        access_token = long_lived_data.get("access_token")
        # Long-lived tokens last 60 days (~5184000 seconds)
        expires_in = long_lived_data.get("expires_in", 5184000)
        expires_at = time.time() + expires_in

        # Step 3: Resolve Instagram Business Account ID
        accounts_url = "https://graph.facebook.com/v19.0/me/accounts"
        resp = await client.get(accounts_url, params={"access_token": access_token})
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Failed to fetch Facebook accounts: {resp.text}")
        
        pages = resp.json().get("data", [])
        ig_user_id = None

        for page in pages:
            page_id = page.get("id")
            page_info_url = f"https://graph.facebook.com/v19.0/{page_id}"
            page_resp = await client.get(page_info_url, params={
                "fields": "instagram_business_account",
                "access_token": access_token
            })
            if page_resp.status_code == 200:
                ig_data = page_resp.json().get("instagram_business_account")
                if ig_data:
                    ig_user_id = ig_data.get("id")
                    break
        
        if not ig_user_id:
            raise HTTPException(status_code=400, detail="No Instagram Business or Creator account linked to this Facebook account.")

        # Step 4: Save token
        token_to_save = {
            "access_token": access_token,
            "token_type": long_lived_data.get("token_type", "bearer"),
            "expires_at": expires_at,
            "ig_user_id": ig_user_id
        }
        _save_token(state, token_to_save)

        return {
            "status": "authenticated",
            "user_id": state,
            "ig_user_id": ig_user_id
        }

@router.post("/upload/{user_id}")
async def upload_reel(user_id: str, req: InstagramUploadRequest):
    """Executes the three-step Reels publishing flow: Container -> Poll -> Publish."""
    token_data = await _get_valid_token(user_id)
    access_token = token_data["access_token"]
    ig_user_id = token_data["ig_user_id"]

    async with httpx.AsyncClient() as client:
        # Step 1: Create media container
        container_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"
        container_params = {
            "media_type": "REELS",
            "video_url": req.video_url,
            "caption": req.caption,
            "access_token": access_token
        }
        if req.cover_url:
            container_params["cover_url"] = req.cover_url

        resp = await client.post(container_url, params=container_params)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Media container creation failed: {resp.text}")
        
        container_id = resp.json().get("id")

        # Step 2: Poll container status
        poll_count = 0
        while poll_count < 24: # 24 * 5s = 2 minutes
            await httpx.AsyncClient().get("https://example.com") # Dummy wait for context, actually use sleep
            time.sleep(5) 
            poll_count += 1
            
            status_url = f"https://graph.facebook.com/v19.0/{container_id}"
            status_resp = await client.get(status_url, params={
                "fields": "status_code",
                "access_token": access_token
            })
            
            if status_resp.status_code == 200:
                status_code = status_resp.json().get("status_code")
                if status_code == "FINISHED":
                    break
                elif status_code == "ERROR":
                    raise HTTPException(status_code=500, detail="Instagram rejected the video during processing. Check video format (MP4, H.264, max 90s for Reels).")
            
        else:
            raise HTTPException(status_code=500, detail=f"Video processing timed out. The container_id is {container_id}. Check Meta manually.")

        # Step 3: Publish container
        publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"
        publish_params = {
            "creation_id": container_id,
            "access_token": access_token
        }
        publish_resp = await client.post(publish_url, params=publish_params)
        if publish_resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Publication failed: {publish_resp.text}")
        
        media_id = publish_resp.json().get("id")

        return {
            "status": "uploaded",
            "media_id": media_id,
            "ig_user_id": ig_user_id
        }

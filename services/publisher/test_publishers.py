import os
import json
import pytest
import importlib
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pathlib import Path

# Required Env Vars for each publisher
YOUTUBE_ENV = {
    "YOUTUBE_CLIENT_ID": "yt_id",
    "YOUTUBE_CLIENT_SECRET": "yt_secret",
    "YOUTUBE_REDIRECT_URI": "http://localhost/yt/callback"
}

TIKTOK_ENV = {
    "TIKTOK_CLIENT_KEY": "tk_key",
    "TIKTOK_CLIENT_SECRET": "tk_secret",
    "TIKTOK_REDIRECT_URI": "http://localhost/tk/callback"
}

INSTAGRAM_ENV = {
    "INSTAGRAM_APP_ID": "ig_id",
    "INSTAGRAM_APP_SECRET": "ig_secret",
    "INSTAGRAM_REDIRECT_URI": "http://localhost/ig/callback"
}

ALL_ENV = {**YOUTUBE_ENV, **TIKTOK_ENV, **INSTAGRAM_ENV}

# Initial import with env vars to satisfy startup validation
with patch.dict(os.environ, ALL_ENV):
    import services.publisher.youtube as youtube_mod
    import services.publisher.tiktok as tiktok_mod
    import services.publisher.instagram as instagram_mod

@pytest.fixture
def yt_app():
    with patch.dict(os.environ, YOUTUBE_ENV):
        importlib.reload(youtube_mod)
        app = FastAPI()
        app.include_router(youtube_mod.router)
        return app

@pytest.fixture
def tk_app():
    with patch.dict(os.environ, TIKTOK_ENV):
        importlib.reload(tiktok_mod)
        app = FastAPI()
        app.include_router(tiktok_mod.router)
        return app

@pytest.fixture
def ig_app():
    with patch.dict(os.environ, INSTAGRAM_ENV):
        importlib.reload(instagram_mod)
        app = FastAPI()
        app.include_router(instagram_mod.router)
        return app

# --- YOUTUBE TESTS ---

def test_youtube_missing_env_var():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as excinfo:
            importlib.reload(youtube_mod)
        assert "Missing required YouTube environment variables" in str(excinfo.value)

def test_youtube_get_auth_url(yt_app):
    client = TestClient(yt_app, raise_server_exceptions=False)
    response = client.get("/auth/user123")
    assert response.status_code == 200
    assert "auth_url" in response.json()
    assert "accounts.google.com" in response.json()["auth_url"]

def test_youtube_upload_no_token(yt_app):
    yt_app.dependency_overrides[youtube_mod._load_token] = lambda user_id: None
    client = TestClient(yt_app, raise_server_exceptions=False)
    response = client.post("/upload/user123", json={
        "video_path": "/fake/video.mp4",
        "title": "Test Video",
        "description": "Test"
    })
    assert response.status_code == 401
    assert "not authenticated" in response.json()["detail"].lower()

@patch("services.publisher.youtube.build")
@patch("services.publisher.youtube._build_credentials")
@patch("services.publisher.youtube._load_token")
@patch("os.path.exists", return_value=True)
def test_youtube_upload_success(mock_exists, mock_load, mock_build_creds, mock_discovery_build, yt_app):
    mock_load.return_value = {"token": "fake"}
    mock_build_creds.return_value = MagicMock()
    
    mock_service = MagicMock()
    mock_discovery_build.return_value = mock_service
    
    mock_request = MagicMock()
    mock_service.videos().insert.return_value = mock_request
    mock_request.next_chunk.return_value = (None, {"id": "test_video_id", "status": {"uploadStatus": "uploaded"}})
    
    client = TestClient(yt_app, raise_server_exceptions=True)
    response = client.post("/upload/user123", json={
        "video_path": "/fake/video.mp4",
        "title": "Test Video",
        "description": "Test",
        "tags": [],
        "privacy": "private"
    })
        
    assert response.status_code == 200
    assert response.json()["video_id"] == "test_video_id"

# --- TIKTOK TESTS ---

def test_tiktok_missing_env_var():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as excinfo:
            importlib.reload(tiktok_mod)
        assert "Missing required TikTok environment variables" in str(excinfo.value)

def test_tiktok_get_auth_url(tk_app):
    client = TestClient(tk_app, raise_server_exceptions=False)
    response = client.get("/auth/user123")
    assert response.status_code == 200
    assert "auth_url" in response.json()
    assert "tiktok.com" in response.json()["auth_url"]

def test_tiktok_upload_no_token(tk_app):
    tk_app.dependency_overrides[tiktok_mod._load_token] = lambda user_id: None
    client = TestClient(tk_app, raise_server_exceptions=False)
    response = client.post("/upload/user123", json={
        "video_path": "/fake/video.mp4",
        "title": "Test Title"
    })
    assert response.status_code == 401

def test_tiktok_title_too_long(tk_app):
    client = TestClient(tk_app, raise_server_exceptions=False)
    response = client.post("/upload/user123", json={
        "video_path": "/fake/video.mp4",
        "title": "a" * 151
    })
    assert response.status_code == 422
    assert "150" in str(response.json()["detail"])

import httpx
def test_tiktok_upload_success(tk_app):
    mock_post = AsyncMock()
    mock_put = AsyncMock()
    
    # Mock Init
    mock_init_resp = MagicMock()
    mock_init_resp.status_code = 200
    mock_init_resp.json.return_value = {
        "data": {"publish_id": "pub_123", "upload_url": "https://fake.upload.url"},
        "error": {"code": "ok"}
    }
    
    # Mock Poll
    mock_poll_resp = MagicMock()
    mock_poll_resp.status_code = 200
    mock_poll_resp.json.return_value = {"data": {"status": "PUBLISH_COMPLETE"}}
    
    mock_post.side_effect = [mock_init_resp, mock_poll_resp]
    mock_put.return_value = MagicMock(status_code=200)
    
    tk_app.dependency_overrides[tiktok_mod._get_valid_token] = AsyncMock(return_value="fake_token")
    
    with patch("httpx.AsyncClient.post", new=mock_post), \
         patch("httpx.AsyncClient.put", new=mock_put), \
         patch("os.path.exists", return_value=True), \
         patch("os.path.getsize", return_value=1024), \
         patch("time.sleep", return_value=None):
        
        client = TestClient(tk_app, raise_server_exceptions=False)
        response = client.post("/upload/user123", json={
            "video_path": "/fake/video.mp4",
            "title": "Test Video"
        })
        
        assert response.status_code == 200
        assert response.json()["publish_id"] == "pub_123"

# --- INSTAGRAM TESTS ---

def test_instagram_missing_env_var():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as excinfo:
            importlib.reload(instagram_mod)
        assert "Missing required Instagram environment variables" in str(excinfo.value)

def test_instagram_get_auth_url(ig_app):
    client = TestClient(ig_app, raise_server_exceptions=False)
    response = client.get("/auth/user123")
    assert response.status_code == 200
    assert "auth_url" in response.json()
    assert "facebook.com" in response.json()["auth_url"]

def test_instagram_upload_no_token(ig_app):
    ig_app.dependency_overrides[instagram_mod._load_token] = lambda user_id: None
    client = TestClient(ig_app, raise_server_exceptions=False)
    response = client.post("/upload/user123", json={
        "video_url": "https://example.com/video.mp4",
        "caption": "Test"
    })
    assert response.status_code == 401

def test_instagram_caption_too_long(ig_app):
    client = TestClient(ig_app, raise_server_exceptions=False)
    response = client.post("/upload/user123", json={
        "video_url": "https://example.com/video.mp4",
        "caption": "a" * 2201
    })
    assert response.status_code == 422
    assert "2200" in str(response.json()["detail"])

def test_instagram_invalid_video_url(ig_app):
    client = TestClient(ig_app, raise_server_exceptions=False)
    response = client.post("/upload/user123", json={
        "video_url": "/local/path/video.mp4",
        "caption": "Test"
    })
    assert response.status_code == 422
    assert "publicly accessible" in str(response.json()["detail"]).lower()

def test_instagram_upload_success(ig_app):
    mock_post = AsyncMock()
    mock_get = AsyncMock()
    
    # Mock Container
    mock_container_resp = MagicMock()
    mock_container_resp.status_code = 200
    mock_container_resp.json.return_value = {"id": "container_123"}
    
    # Mock Publish
    mock_publish_resp = MagicMock()
    mock_publish_resp.status_code = 200
    mock_publish_resp.json.return_value = {"id": "media_456"}
    
    # Mock Status
    mock_status_resp = MagicMock()
    mock_status_resp.status_code = 200
    mock_status_resp.json.return_value = {"status_code": "FINISHED"}
    
    mock_post.side_effect = [mock_container_resp, mock_publish_resp]
    mock_get.side_effect = [MagicMock(), mock_status_resp]
    
    ig_app.dependency_overrides[instagram_mod._get_valid_token] = AsyncMock(return_value={"access_token": "fake", "ig_user_id": "ig_123"})
    
    with patch("httpx.AsyncClient.post", new=mock_post), \
         patch("httpx.AsyncClient.get", new=mock_get), \
         patch("time.sleep", return_value=None):
        
        client = TestClient(ig_app, raise_server_exceptions=False)
        response = client.post("/upload/user123", json={
            "video_url": "https://example.com/video.mp4",
            "caption": "Test caption",
            "cover_url": None
        })
        
        assert response.status_code == 200
        assert response.json() == { "status": "uploaded", "media_id": "media_456", "ig_user_id": "ig_123" }

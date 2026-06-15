import os
import time
import pytest
import importlib
import httpx
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pathlib import Path

# Required Env Vars
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

# Initial import with env vars
with patch.dict(os.environ, ALL_ENV):
    import services.publisher.youtube as youtube_mod
    import services.publisher.tiktok as tiktok_mod
    import services.publisher.instagram as instagram_mod

@pytest.fixture
def yt_app():
    with patch.dict(os.environ, YOUTUBE_ENV):
        importlib.reload(youtube_mod)
        app = FastAPI()
        app.include_router(youtube_mod.router, prefix="/publisher/youtube")
        return app

@pytest.fixture
def tk_app():
    with patch.dict(os.environ, TIKTOK_ENV):
        importlib.reload(tiktok_mod)
        app = FastAPI()
        app.include_router(tiktok_mod.router, prefix="/publisher/tiktok")
        return app

@pytest.fixture
def ig_app():
    with patch.dict(os.environ, INSTAGRAM_ENV):
        importlib.reload(instagram_mod)
        app = FastAPI()
        app.include_router(instagram_mod.router, prefix="/publisher/instagram")
        return app

# --- YOUTUBE TESTS ---
def test_youtube_missing_env_var():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError):
            importlib.reload(youtube_mod)

def test_youtube_get_auth_url(yt_app):
    client = TestClient(yt_app, raise_server_exceptions=False)
    response = client.get("/publisher/youtube/auth/user123")
    assert response.status_code == 200
    assert "auth_url" in response.json()

def test_youtube_upload_no_token(yt_app):
    with patch("services.publisher.youtube._load_token", return_value=None):
        client = TestClient(yt_app, raise_server_exceptions=False)
        response = client.post("/publisher/youtube/upload/user123", json={"video_path": "/fake/video.mp4", "title": "Test", "description": "Test"})
        assert response.status_code == 401

def test_youtube_upload_success(yt_app):
    with patch("services.publisher.youtube.build") as mock_build, \
         patch("services.publisher.youtube._build_credentials") as mock_creds, \
         patch("services.publisher.youtube._load_token") as mock_load_token, \
         patch("services.publisher.youtube.os.path.exists", return_value=True), \
         patch("services.publisher.youtube.MediaFileUpload"):
        
        mock_load_token.return_value = {"token": "fake"}
        mock_creds.return_value = MagicMock(expired=False)
        mock_build.return_value.videos.return_value.insert.return_value.next_chunk.return_value = (None, {"id": "test_video_id"})
        
        client = TestClient(yt_app, raise_server_exceptions=False)
        response = client.post("/publisher/youtube/upload/user123", json={
            "video_path": "/fake/video.mp4", "title": "Test", "description": "Test", "tags": [], "privacy": "private"
        })
        assert response.status_code == 200
        assert response.json()["video_id"] == "test_video_id"

# --- TIKTOK TESTS ---
def test_tiktok_missing_env_var():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError):
            importlib.reload(tiktok_mod)

def test_tiktok_get_auth_url(tk_app):
    client = TestClient(tk_app, raise_server_exceptions=False)
    response = client.get("/publisher/tiktok/auth/user123")
    assert response.status_code == 200
    assert "auth_url" in response.json()

def test_tiktok_upload_no_token(tk_app):
    with patch("services.publisher.tiktok._load_token", return_value=None):
        client = TestClient(tk_app, raise_server_exceptions=False)
        response = client.post("/publisher/tiktok/upload/user123", json={"video_path": "/fake/video.mp4", "title": "Test"})
        assert response.status_code == 401

def test_tiktok_title_too_long(tk_app):
    client = TestClient(tk_app, raise_server_exceptions=False)
    response = client.post("/publisher/tiktok/upload/user123", json={"video_path": "/fake/video.mp4", "title": "a" * 151})
    assert response.status_code == 422

class MockAsyncClient:
    def __init__(self, *args, **kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def post(self, *args, **kwargs):
        if 'init' in args[0]:
             return MagicMock(json=lambda: {"data": {"publish_id": "pub_123", "upload_url": "http://fake.url"}, "error": {"code": "ok"}}, status_code=200)
        return MagicMock(json=lambda: {"data": {"status": "PUBLISH_COMPLETE"}}, status_code=200)
    async def put(self, *args, **kwargs):
        return MagicMock(status_code=200)

def test_tiktok_upload_success(tk_app):
    with patch("services.publisher.tiktok._load_token") as mock_load_token, \
         patch("services.publisher.tiktok._get_valid_token") as mock_get_token, \
         patch("services.publisher.tiktok.os.path.exists", return_value=True), \
         patch("services.publisher.tiktok.os.path.getsize", return_value=1024), \
         patch("services.publisher.tiktok.httpx.AsyncClient", new=MockAsyncClient), \
         patch("builtins.open", new_callable=MagicMock):
        
        mock_load_token.return_value = {"access_token": "fake", "expires_at": time.time() + 3600}
        mock_get_token.return_value = "fake_access_token"
        
        client = TestClient(tk_app, raise_server_exceptions=False)
        response = client.post("/publisher/tiktok/upload/user123", json={"video_path": "/fake/video.mp4", "title": "Test"})
        assert response.status_code == 200
        assert "publish_id" in response.json()

# --- INSTAGRAM TESTS ---
def test_instagram_missing_env_var():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError):
            importlib.reload(instagram_mod)

def test_instagram_get_auth_url(ig_app):
    client = TestClient(ig_app, raise_server_exceptions=False)
    response = client.get("/publisher/instagram/auth/user123")
    assert response.status_code == 200
    assert "auth_url" in response.json()

def test_instagram_upload_no_token(ig_app):
    with patch("services.publisher.instagram._load_token", return_value=None):
        client = TestClient(ig_app, raise_server_exceptions=False)
        response = client.post("/publisher/instagram/upload/user123", json={"video_url": "https://example.com/v.mp4", "caption": "Test"})
        assert response.status_code == 401

def test_instagram_caption_too_long(ig_app):
    client = TestClient(ig_app, raise_server_exceptions=False)
    response = client.post("/publisher/instagram/upload/user123", json={"video_url": "https://example.com/v.mp4", "caption": "a" * 2201})
    assert response.status_code == 422

def test_instagram_invalid_video_url(ig_app):
    client = TestClient(ig_app, raise_server_exceptions=False)
    response = client.post("/publisher/instagram/upload/user123", json={"video_url": "/local/v.mp4", "caption": "Test"})
    assert response.status_code == 422

class MockAsyncClientIG:
    def __init__(self, *args, **kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def post(self, *args, **kwargs):
        if 'media' in args[0]: return MagicMock(json=lambda: {'id': 'container_123'}, status_code=200)
        return MagicMock(json=lambda: {'id': 'media_456'}, status_code=200)
    async def get(self, *args, **kwargs):
        return MagicMock(json=lambda: {'status_code': 'FINISHED'}, status_code=200)

def test_instagram_upload_success(ig_app):
    with patch("services.publisher.instagram._load_token") as mock_load_token, \
         patch("services.publisher.instagram._get_valid_token") as mock_get_token, \
         patch("services.publisher.instagram.httpx.AsyncClient", new=MockAsyncClientIG):
        
        fake_token = {"access_token": "fake", "ig_user_id": "ig_123"}
        mock_load_token.return_value = fake_token
        mock_get_token.return_value = fake_token
        
        client = TestClient(ig_app, raise_server_exceptions=False)
        response = client.post("/publisher/instagram/upload/user123", json={"video_url": "https://example.com/v.mp4", "caption": "Test", "cover_url": None})
        assert response.status_code == 200
        assert response.json()["media_id"] == "container_123"

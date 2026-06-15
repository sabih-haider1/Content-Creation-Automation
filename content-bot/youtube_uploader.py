import os
import json
import httplib2
import socks
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import google_auth_httplib2
from config import YOUTUBE_CLIENT_SECRET_FILE

# OAuth Scope for YouTube video uploads
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]

def get_token_path(user_id: int) -> str:
    """
    Returns the path to the token file for a specific user.
    """
    tokens_dir = "tokens"
    if not os.path.exists(tokens_dir):
        os.makedirs(tokens_dir)
    return os.path.join(tokens_dir, f"token_{user_id}.json")

# Tor Proxy Config
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 9150 # Tor Browser port

def get_proxied_http():
    """
    Creates an httplib2.Http object configured to use the Tor SOCKS5 proxy.
    This is necessary for googleapiclient to work via Tor.
    """
    return httplib2.Http(proxy_info=httplib2.ProxyInfo(
        proxy_type=httplib2.socks.PROXY_TYPE_SOCKS5,
        proxy_host=PROXY_HOST,
        proxy_port=PROXY_PORT,
        proxy_rdns=True # Equivalent to socks5h (Remote DNS)
    ))

def get_authorization_url(user_id: int):
    """
    Generates the authorization URL for the user to visit.
    Returns (auth_url, flow_object)
    """
    if not os.path.exists(YOUTUBE_CLIENT_SECRET_FILE):
        raise FileNotFoundError(f"YouTube client secret file '{YOUTUBE_CLIENT_SECRET_FILE}' not found.")
    
    flow = InstalledAppFlow.from_client_secrets_file(
        YOUTUBE_CLIENT_SECRET_FILE, 
        SCOPES,
        redirect_uri="http://localhost"
    )
    
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    return auth_url, flow

def complete_authorization(user_id: int, flow, authorization_response: str):
    """
    Exchanges the authorization response (the URL the user was redirected to) for tokens.
    """
    # The authorization_response is the full URL the user was redirected to, e.g.,
    # http://localhost/?state=...&code=4/0Af...&scope=...
    
    # Ensure the URL is https if required by the library (though localhost is usually fine as http)
    if authorization_response.startswith("http://") and "localhost" not in authorization_response:
        authorization_response = authorization_response.replace("http://", "https://", 1)

    flow.fetch_token(authorization_response=authorization_response)
    creds = flow.credentials
    
    token_file = get_token_path(user_id)
    with open(token_file, "w") as token:
        token.write(creds.to_json())
        
    return creds

def get_youtube_credentials(user_id: int):
    """
    Retrieves and refreshes YouTube OAuth credentials for a specific user.
    Note: This no longer runs the local server automatically.
    """
    token_file = get_token_path(user_id)
    creds = None
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception as e:
            print(f"Error loading {token_file}: {e}")
            
    if creds and creds.expired and creds.refresh_token:
        try:
            import requests
            proxies = {
                'http': f'socks5h://{PROXY_HOST}:{PROXY_PORT}',
                'https': f'socks5h://{PROXY_HOST}:{PROXY_PORT}'
            }
            from google.auth.transport.requests import Request as GoogleRequest
            session = requests.Session()
            session.proxies.update(proxies)
            creds.refresh(GoogleRequest(session=session))
            
            with open(token_file, "w") as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"Error refreshing token for user {user_id}: {e}")
            creds = None
            
    return creds

def get_authenticated_service(user_id: int):
    """
    Builds the YouTube service using a proxied httplib2 object.
    """
    creds = get_youtube_credentials(user_id)
    # Create the base proxied http object
    http_base = get_proxied_http()
    # Use google_auth_httplib2 to wrap the credentials around the proxied http client
    # This is the correct way for modern google-auth
    authorized_http = google_auth_httplib2.AuthorizedHttp(creds, http=http_base)
    
    return build("youtube", "v3", http=authorized_http)

def check_connection(user_id: int):
    """
    Verifies if the YouTube account is connected by fetching channel info.
    """
    try:
        youtube = get_authenticated_service(user_id)
        request = youtube.channels().list(part="snippet", mine=True)
        response = request.execute()
        if "items" in response and len(response["items"]) > 0:
            return response["items"][0]["snippet"]["title"]
        return "Unknown Channel"
    except Exception as e:
        print(f"Connection check failed for user {user_id}: {e}")
        return None

def upload_video(user_id: int, video_path: str, title: str, description: str, hashtags: list, publish_at: str = None) -> str:
    """
    Uploads a video to YouTube. Supports immediate public upload or scheduling.
    publish_at should be ISO 8601 string (e.g. 2026-06-12T15:00:00Z)
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")
        
    try:
        youtube = get_authenticated_service(user_id)
        
        tags_text = " ".join([f"#{tag.replace('#', '')}" for tag in hashtags])
        full_description = f"{description}\n\n{tags_text}\n\nGenerated by Gemini Veo 2 Bot"
        
        # Status logic: if scheduled, privacy must be 'private'
        status_config = {
            "selfDeclaredMadeForKids": False
        }
        
        if publish_at:
            status_config["privacyStatus"] = "private"
            status_config["publishAt"] = publish_at
        else:
            status_config["privacyStatus"] = "public"
        
        body = {
            "snippet": {
                "title": title[:100],
                "description": full_description[:5000],
                "tags": [tag.replace("#", "") for tag in hashtags][:50],
                "categoryId": "27"
            },
            "status": status_config
        }
        
        media = MediaFileUpload(
            video_path,
            chunksize=1024*1024, # 1MB chunks for stability
            resumable=True,
            mimetype="video/mp4"
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
                print(f"Uploading: {int(status.progress() * 100)}%")
                
        video_id = response.get("id")
        if not video_id:
            raise Exception("Upload succeeded but no Video ID was returned.")
            
        return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        print(f"YouTube Upload Critical Error: {e}")
        raise e

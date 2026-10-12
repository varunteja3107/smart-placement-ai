import os

# Local development only: OAuth callback uses loopback HTTP.
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
import secrets
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

router = APIRouter()
REDIRECT_URI = (
    "http://127.0.0.1:8000/api/integrations/google/drive/callback"
)
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

PRIVATE_DIR = BASE_DIR / ".private"
TOKEN_FILE = PRIVATE_DIR / "google_drive_token.json"

# Temporary OAuth state is held in memory for local development.
_pending_states: dict[str, float] = {}


def credentials_configured():
    return bool(
        os.getenv("GOOGLE_CLIENT_ID")
        and os.getenv("GOOGLE_CLIENT_SECRET")
    )


def create_flow(state=None):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth credentials are not configured in backend/.env.",
        )

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }

    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI,
    )


def save_credentials(credentials):
    PRIVATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    TOKEN_FILE.write_text(credentials.to_json())
    TOKEN_FILE.chmod(0o600)


def get_credentials():
    if not TOKEN_FILE.exists():
        raise HTTPException(
            status_code=401,
            detail="Google Drive is not connected. Visit the connect endpoint first.",
        )

    try:
        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE), scopes=SCOPES
        )
    except (ValueError, OSError):
        raise HTTPException(
            status_code=401,
            detail="Saved Google authorization is invalid. Reconnect Google Drive.",
        )

    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(GoogleRequest())
            save_credentials(credentials)
        except Exception:
            raise HTTPException(
                status_code=401,
                detail="Google authorization expired. Reconnect Google Drive.",
            )

    if not credentials.valid:
        raise HTTPException(
            status_code=401,
            detail="Google Drive authorization is not valid. Reconnect Google Drive.",
        )

    return credentials


@router.get("/api/integrations/google/drive/connect")
def connect_google_drive():
    state = secrets.token_urlsafe(32)
    now = time.time()

    # Remove expired states and set a short lifetime for the new one.
    for old_state, expiry in list(_pending_states.items()):
        if expiry < now:
            _pending_states.pop(old_state, None)

    _pending_states[state] = now + 600

    flow = create_flow(state=state)
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    return RedirectResponse(authorization_url, status_code=302)


@router.get("/api/integrations/google/drive/callback")
def google_drive_callback(request: Request):
    if request.query_params.get("error"):
        raise HTTPException(
            status_code=400,
            detail="Google authorization was cancelled or denied.",
        )

    state = request.query_params.get("state", "")
    expiry = _pending_states.pop(state, None)

    if not expiry or expiry < time.time():
        raise HTTPException(
            status_code=400,
            detail="OAuth state is invalid or expired. Start the connection again.",
        )

    if not request.query_params.get("code"):
        raise HTTPException(
            status_code=400,
            detail="Google did not return an authorization code.",
        )

    flow = create_flow(state=state)

    try:
        flow.fetch_token(authorization_response=str(request.url))
        credentials = flow.credentials
        save_credentials(credentials)
    except Exception as exc:
        error_type = type(exc).__name__
        print(f"Google Drive OAuth exchange failed: {error_type}")

        safe_reasons = {
            "InsecureTransportError": "Local OAuth transport was rejected. Restart the backend after applying the local-development setting.",
            "MismatchingStateError": "OAuth state mismatch. Start a fresh connection attempt.",
            "InvalidGrantError": "Google rejected the authorization code. Check the client secret and redirect URI, then reconnect.",
            "InvalidClientError": "Google rejected the OAuth client credentials. Check the configured client ID and replacement secret.",
            "TokenExpiredError": "The authorization code expired. Start a fresh connection attempt.",
        }
        reason = safe_reasons.get(
            error_type,
            "Check the OAuth client credentials and exact redirect URI, then try again.",
        )
        raise HTTPException(
            status_code=400,
            detail=f"Google authorization failed ({error_type}). {reason}",
        )

    return {
        "connected": True,
        "source": "Google Drive",
        "message": "Google Drive authorization succeeded.",
        "next": "/api/integrations/google/drive/files",
    }


@router.get("/api/integrations/google/drive/status")
def google_drive_status():
    return {
        "configured": credentials_configured(),
        "connected": TOKEN_FILE.exists(),
        "source": "Google Drive",
        "mode": "local development",
    }


@router.get("/api/integrations/google/drive/files")
def list_google_drive_files(
    page_size: int = Query(20, ge=1, le=100),
    page_token: str | None = Query(None, max_length=2000),
):
    credentials = get_credentials()

    try:
        service = build(
            "drive",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

        params = {
            "pageSize": page_size,
            "orderBy": "modifiedTime desc",
            "q": "trashed = false",
            "fields": (
                "nextPageToken,files("
                "id,name,mimeType,modifiedTime,webViewLink,description,size"
                ")"
            ),
        }

        if page_token:
            params["pageToken"] = page_token

        result = service.files().list(**params).execute()

        return {
            "source": "Google Drive",
            "count": len(result.get("files", [])),
            "files": result.get("files", []),
            "next_page_token": result.get("nextPageToken"),
        }

    except HttpError as exc:
        print(f"Google Drive API request failed with HTTP {exc.resp.status}")
        raise HTTPException(
            status_code=502,
            detail="Google Drive could not return the file list. Check API access and authorization.",
        )

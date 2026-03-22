"""
app.py  —  Quota Tracker FastAPI Server
----------------------------------------
Handles:
  - Serving the dashboard UI
  - Google OAuth 2.0 login/callback
  - /api/refresh  — runs fetch_quota.fetch_all()
  - /api/quota    — returns current quota_data.json
  - /api/accounts — returns logged-in Google accounts
  - /api/logout   — removes account from session

Run:
    python app.py
    or: uvicorn app:app --reload --host 127.0.0.1 --port 8000
"""

import json, os, secrets, threading, time
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.httpx_client import AsyncOAuth2Client

import fetch_quota as fq

FETCH_INTERVAL = int(os.environ.get("FETCH_INTERVAL", 900))  # 15 minutes default

# ── CONFIG ────────────────────────────────────────────────────────────────────

GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
SESSION_SECRET       = os.environ.get("SESSION_SECRET", secrets.token_hex(32))
HOST                 = os.environ.get("HOST", "127.0.0.1")
PORT                 = int(os.environ.get("PORT", 8000))

REDIRECT_URI         = f"http://{HOST}:{PORT}/auth/callback"
GOOGLE_AUTH_URL      = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL     = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"

BASE_DIR             = Path(__file__).parent
QUOTA_FILE           = BASE_DIR / "quota_data.json"
STATIC_DIR           = BASE_DIR / "static"

# ── APP ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Quota Tracker")

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="quota_session",
    max_age=60 * 60 * 24 * 30,   # 30 days
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main dashboard HTML."""
    html_file = STATIC_DIR / "index.html"
    if not html_file.exists():
        return HTMLResponse("<h2>index.html not found in /static</h2>", status_code=500)
    return HTMLResponse(html_file.read_text(encoding="utf-8"))


@app.get("/auth/google")
async def auth_google(request: Request):
    """Redirect to Google OAuth consent screen."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not set in .env")

    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state

    client = AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        redirect_uri=REDIRECT_URI,
    )
    url, _ = client.create_authorization_url(
        GOOGLE_AUTH_URL,
        state=state,
        scope="openid email profile",
        access_type="offline",
        prompt="select_account",
    )
    return RedirectResponse(url)


@app.get("/auth/callback")
async def auth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Handle Google OAuth callback, store account in session."""
    if error:
        return RedirectResponse("/?error=" + error)

    stored_state = request.session.get("oauth_state")
    if not state or state != stored_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    client = AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
    )

    # Exchange code for token
    token = await client.fetch_token(
        GOOGLE_TOKEN_URL,
        code=code,
        grant_type="authorization_code",
    )

    # Fetch user info
    resp = await client.get(GOOGLE_USERINFO_URL)
    userinfo = resp.json()

    email   = userinfo.get("email", "")
    name    = userinfo.get("name", email)
    picture = userinfo.get("picture", "")

    # Store in session — list of accounts
    accounts = request.session.get("accounts", [])
    existing = next((a for a in accounts if a["email"] == email), None)
    if existing:
        existing["name"]    = name
        existing["picture"] = picture
        existing["token"]   = token.get("access_token", "")
    else:
        accounts.append({
            "email":   email,
            "name":    name,
            "picture": picture,
            "token":   token.get("access_token", ""),
        })
    request.session["accounts"] = accounts

    return RedirectResponse("/")


@app.get("/auth/logout")
async def logout(request: Request, email: str = None):
    """Remove an account from session, or clear all."""
    if email:
        accounts = request.session.get("accounts", [])
        request.session["accounts"] = [a for a in accounts if a["email"] != email]
    else:
        request.session.clear()
    return RedirectResponse("/")


# ── API ROUTES ─────────────────────────────────────────────────────────────────

@app.get("/api/accounts")
async def api_accounts(request: Request):
    """Return currently logged-in Google accounts."""
    accounts = request.session.get("accounts", [])
    # Strip tokens before sending to frontend
    safe = [{"email": a["email"], "name": a["name"], "picture": a["picture"]} for a in accounts]
    return JSONResponse({"accounts": safe})


@app.get("/api/quota")
async def api_quota():
    """Return current quota_data.json."""
    if not QUOTA_FILE.exists():
        return JSONResponse({
            "fetched_at": None,
            "category":   "AI Coding Tools",
            "tools":      [],
            "accounts":   [],
            "message":    "No quota data yet. Click Refresh to fetch.",
        })
    return JSONResponse(json.loads(QUOTA_FILE.read_text(encoding="utf-8")))


@app.post("/api/refresh")
async def api_refresh():
    """Run fetch_all() and return fresh quota data."""
    print(f"[API] Refresh triggered at {datetime.now().isoformat()}")
    try:
        payload = fq.fetch_all(push=False)
        return JSONResponse({"status": "ok", "data": payload})
    except Exception as e:
        print(f"[API] Refresh error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def api_status(request: Request):
    """Health check + session info."""
    accounts = request.session.get("accounts", [])
    quota_exists = QUOTA_FILE.exists()
    fetched_at = None
    if quota_exists:
        try:
            fetched_at = json.loads(QUOTA_FILE.read_text())["fetched_at"]
        except Exception:
            pass
    return JSONResponse({
        "status":        "ok",
        "logged_in":     len(accounts),
        "quota_exists":  quota_exists,
        "fetched_at":    fetched_at,
        "google_configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
    })


# ── BACKGROUND FETCH ─────────────────────────────────────────────────────────

def background_fetch_loop():
    """Runs fetch_all() on startup then every FETCH_INTERVAL seconds."""
    # Initial fetch on startup
    print(f"[AUTO] Initial fetch on startup...")
    try:
        fq.fetch_all(push=False)
        print(f"[AUTO] Initial fetch complete")
    except Exception as e:
        print(f"[AUTO] Initial fetch error: {e}")

    while True:
        time.sleep(FETCH_INTERVAL)
        print(f"[AUTO] Auto-fetch at {datetime.now().strftime('%H:%M:%S')} (every {FETCH_INTERVAL//60}min)")
        try:
            fq.fetch_all(push=False)
        except Exception as e:
            print(f"[AUTO] Auto-fetch error: {e}")


# ── STARTUP ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("  Quota Tracker — AI Coding Tools")
    print(f"  http://{HOST}:{PORT}")
    print(f"  Auto-fetch every {FETCH_INTERVAL//60} minutes")
    print("=" * 50)
    if not GOOGLE_CLIENT_ID:
        print("  ⚠  GOOGLE_CLIENT_ID not set — OAuth disabled")
    else:
        print(f"  ✓  Google OAuth configured")
    if not fq.find_ag_cli():
        print("  ⚠  antigravity-usage CLI not found - cached Antigravity data will be reused if available")
    else:
        print("  ✓  Antigravity CLI found")
    print("=" * 50)

    # Start background fetch thread (daemon — dies with main process)
    t = threading.Thread(target=background_fetch_loop, daemon=True)
    t.start()


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=HOST, port=PORT, reload=False)

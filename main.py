"""
╔══════════════════════════════════════════╗
   YouTube Search + Download API
   Built with FastAPI + yt-dlp
   Deploy: Railway / Render
╚══════════════════════════════════════════╝
"""

import os
import asyncio
import hashlib
from pathlib import Path
from contextlib import asynccontextmanager

import yt_dlp
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Header
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

MAX_CACHE_FILES = 50   # zyada files hone par purani delete ho jaayengi

# ─────────────────────────────────────────────
#  API KEYS — multiple users support
#  Naya key add karna ho toh bas list mein daal do
# ─────────────────────────────────────────────
API_KEYS = {
    "24bc91436add00eeda4d0b50b9f073fc": "ARUxMUSIC (main bot)",   # tera main bot
    # "abcdef1234567890abcdef1234567890": "Kisi aur ka bot",       # example
}

def _check_key(x_api_key: str = None):
    if not x_api_key or x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key. Header: x-api-key")

def _gen_key() -> str:
    import secrets
    return secrets.token_hex(16)


# ─────────────────────────────────────────────
#  CLEANUP OLD FILES (background)
# ─────────────────────────────────────────────
def cleanup_old_files():
    files = sorted(DOWNLOAD_DIR.glob("*"), key=lambda f: f.stat().st_mtime)
    while len(files) > MAX_CACHE_FILES:
        try:
            files.pop(0).unlink()
        except:
            pass


# ─────────────────────────────────────────────
#  APP INIT
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    yield

app = FastAPI(
    title="YouTube API",
    description="Search, Audio & Video download API powered by yt-dlp",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def _short_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:10]


def _run_ydl(opts: dict, url: str):
    """Synchronous yt-dlp call — executor mein run hoga."""
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=True)


def _run_ydl_no_dl(opts: dict, url: str):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def _fmt_duration(seconds: int) -> str:
    if not seconds:
        return "0:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def _entry_to_dict(entry: dict) -> dict:
    vid_id = entry.get("id", "")
    return {
        "id":         vid_id,
        "title":      entry.get("title", "Unknown"),
        "channel":    entry.get("uploader") or entry.get("channel", ""),
        "duration":   int(entry.get("duration") or 0),
        "duration_fmt": _fmt_duration(entry.get("duration")),
        "views":      entry.get("view_count", 0),
        "thumbnail":  f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg",
        "url":        f"https://www.youtube.com/watch?v={vid_id}",
    }


# ─────────────────────────────────────────────
#  MASTER KEY — sirf tere paas hoga
#  /genkey aur /keys sirf isse access honge
# ─────────────────────────────────────────────
MASTER_KEY = "aru-master-7450385463"   # apni marzi se badal lo

# ─────────────────────────────────────────────
#  COOKIES — YouTube bot detection bypass
#  cookies.txt file repo mein rakhni hai
# ─────────────────────────────────────────────
COOKIES_FILE = "cookies.txt" if os.path.exists("cookies.txt") else None

def _base_opts() -> dict:
    """Common yt-dlp options — cookies automatically add hoti hain agar file hai."""
    opts = {
        "quiet":       True,
        "no_warnings": True,
        "noplaylist":  True,
    }
    if COOKIES_FILE:
        opts["cookiefile"] = COOKIES_FILE
    return opts

# ─────────────────────────────────────────────
#  ROOT
# ─────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name":    "YouTube API",
        "version": "1.0.0",
        "author":  "ARU x API",
        "endpoints": {
            "search":   "/search?query=<query>&limit=<1-10>",
            "audio":    "/audio?query=<query or yt url>",
            "video":    "/video?query=<query or yt url>",
            "info":     "/info?query=<query or yt url>",
            "download": "/download?file=<filename>  (internal use)",
        },
    }


# ─────────────────────────────────────────────
#  KEY MANAGEMENT (sirf master key se)
# ─────────────────────────────────────────────

@app.get("/genkey")
async def genkey(
    label: str = Query(..., description="Is key ka naam / kiske liye hai"),
    x_api_key: str = Header(None),
):
    """Naya API key generate karo — sirf master key se."""
    if x_api_key != MASTER_KEY:
        raise HTTPException(403, "Master key chahiye!")
    new_key = _gen_key()
    API_KEYS[new_key] = label
    return {
        "key":   new_key,
        "label": label,
        "msg":   "Key generate ho gayi! main.py mein API_KEYS mein save karo."
    }


@app.get("/keys")
async def list_keys(
    x_api_key: str = Header(None),
):
    """Saari active keys dekho — sirf master key se."""
    if x_api_key != MASTER_KEY:
        raise HTTPException(403, "Master key chahiye!")
    return {
        "total": len(API_KEYS),
        "keys":  [{"key": k, "label": v} for k, v in API_KEYS.items()]
    }


@app.delete("/revokekey")
async def revoke_key(
    key: str = Query(..., description="Revoke karne wali key"),
    x_api_key: str = Header(None),
):
    """Kisi ki key band karo — sirf master key se."""
    if x_api_key != MASTER_KEY:
        raise HTTPException(403, "Master key chahiye!")
    if key not in API_KEYS:
        raise HTTPException(404, "Key mili nahi!")
    label = API_KEYS.pop(key)
    return {"msg": f"Key revoke ho gayi!", "label": label}


# ─────────────────────────────────────────────
#  1. SEARCH
#  GET /search?query=shape+of+you&limit=5
# ─────────────────────────────────────────────
@app.get("/search")
async def search(
    query: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=10, description="Number of results (1-10)"),
    x_api_key: str = Header(None, description="API Key"),
):
    _check_key(x_api_key)
    loop = asyncio.get_event_loop()
    opts = {**_base_opts(), "extract_flat": True}

    try:
        info = await loop.run_in_executor(
            None, _run_ydl_no_dl, opts, f"ytsearch{limit}:{query}"
        )
    except Exception as e:
        raise HTTPException(502, f"Search failed: {e}")

    entries = info.get("entries") or []
    results = [_entry_to_dict(e) for e in entries if e]

    return {
        "query":   query,
        "count":   len(results),
        "results": results,
    }


# ─────────────────────────────────────────────
#  2. INFO
#  GET /info?query=<yt url or search term>
# ─────────────────────────────────────────────
@app.get("/info")
async def info(
    query: str = Query(..., description="YouTube URL or search query"),
    x_api_key: str = Header(None, description="API Key"),
):
    _check_key(x_api_key)
    loop = asyncio.get_event_loop()

    is_url = query.startswith("http")
    url    = query if is_url else f"ytsearch1:{query}"

    opts = {**_base_opts(), "extract_flat": not is_url}

    try:
        raw = await loop.run_in_executor(None, _run_ydl_no_dl, opts, url)
    except Exception as e:
        raise HTTPException(502, f"Info fetch failed: {e}")

    # Search result → first entry
    if not is_url and "entries" in raw:
        entries = raw.get("entries") or []
        if not entries:
            raise HTTPException(404, "No results found")
        raw = entries[0]

    return _entry_to_dict(raw)


# ─────────────────────────────────────────────
#  3. AUDIO DOWNLOAD
#  GET /audio?query=<yt url or search>
# ─────────────────────────────────────────────
@app.get("/audio")
async def audio(
    query: str = Query(..., description="YouTube URL or search query"),
    background_tasks: BackgroundTasks = None,
    x_api_key: str = Header(None, description="API Key"),
):
    _check_key(x_api_key)
    loop   = asyncio.get_event_loop()
    is_url = query.startswith("http")
    url    = query if is_url else f"ytsearch1:{query}"
    fid    = _short_id(query)
    out    = DOWNLOAD_DIR / f"{fid}.mp3"

    # Cache check
    if not out.exists():
        opts = {
            **_base_opts(),
            "format":         "bestaudio/best",
            "outtmpl":        str(DOWNLOAD_DIR / f"{fid}.%(ext)s"),
            "postprocessors": [{
                "key":              "FFmpegExtractAudio",
                "preferredcodec":   "mp3",
                "preferredquality": "192",
            }],
        }
        try:
            await loop.run_in_executor(None, _run_ydl, opts, url)
        except Exception as e:
            raise HTTPException(502, f"Audio download failed: {e}")

        if not out.exists():
            raise HTTPException(500, "File not created. ffmpeg installed hai?")

    if background_tasks:
        background_tasks.add_task(cleanup_old_files)

    return FileResponse(
        path=out,
        media_type="audio/mpeg",
        filename=out.name,
        headers={"Content-Disposition": f'attachment; filename="{out.name}"'},
    )


# ─────────────────────────────────────────────
#  4. VIDEO DOWNLOAD
#  GET /video?query=<yt url or search>
# ─────────────────────────────────────────────
@app.get("/video")
async def video(
    query:   str = Query(..., description="YouTube URL or search query"),
    quality: str = Query("720", description="Quality: 360, 480, 720, 1080"),
    background_tasks: BackgroundTasks = None,
    x_api_key: str = Header(None, description="API Key"),
):
    _check_key(x_api_key)
    loop   = asyncio.get_event_loop()
    is_url = query.startswith("http")
    url    = query if is_url else f"ytsearch1:{query}"
    fid    = _short_id(f"{query}_{quality}")
    out    = DOWNLOAD_DIR / f"{fid}.mp4"

    if not out.exists():
        # Flexible format — jo bhi available ho usse mp4 mein convert karo
        fmt = (
            f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
            f"/bestvideo+bestaudio/best"
        )
        opts = {
            **_base_opts(),
            "format":              fmt,
            "outtmpl":             str(DOWNLOAD_DIR / f"{fid}.%(ext)s"),
            "merge_output_format": "mp4",
            "postprocessors": [{
                "key":               "FFmpegVideoConvertor",
                "preferedformat":    "mp4",
            }],
        }
        try:
            await loop.run_in_executor(None, _run_ydl, opts, url)
        except Exception as e:
            raise HTTPException(502, f"Video download failed: {e}")

        if not out.exists():
            raise HTTPException(500, "File not created. ffmpeg installed hai?")

    if background_tasks:
        background_tasks.add_task(cleanup_old_files)

    return FileResponse(
        path=out,
        media_type="video/mp4",
        filename=out.name,
        headers={"Content-Disposition": f'attachment; filename="{out.name}"'},
    )


# ─────────────────────────────────────────────
#  5. STREAM URL (direct link — no download)
#  GET /stream?query=<yt url or search>&type=audio|video
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
#  5. STREAM (redirects to audio/video download)
#  GET /stream?query=...&type=audio|video
# ─────────────────────────────────────────────
@app.get("/stream")
async def stream_url(
    query:   str = Query(..., description="YouTube URL or search query"),
    type:    str = Query("audio", description="audio or video"),
    quality: str = Query("720", description="Video quality: 360, 480, 720, 1080"),
    background_tasks: BackgroundTasks = None,
    x_api_key: str = Header(None, description="API Key"),
):
    _check_key(x_api_key)
    """
    YouTube direct CDN URL bot-check ki wajah se kaam nahi karti.
    /stream internally /audio ya /video download karke file serve karta hai.
    """
    if type == "video":
        return await video(query=query, quality=quality, background_tasks=background_tasks)
    else:
        return await audio(query=query, background_tasks=background_tasks)

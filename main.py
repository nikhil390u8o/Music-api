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
import imageio_ffmpeg
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Header
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ✅ ffmpeg path set karo
_ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
os.environ["PATH"] += os.pathsep + os.path.dirname(_ffmpeg_exe)
os.environ["FFMPEG_LOCATION"] = _ffmpeg_exe

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

MAX_CACHE_FILES = 50

# ─────────────────────────────────────────────
#  API KEYS
# ─────────────────────────────────────────────
API_KEYS = {
    "24bc91436add00eeda4d0b50b9f073fc": "ARUxMUSIC (main bot)",
}

def _check_key(x_api_key: str = None):
    if not x_api_key or x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key. Header: x-api-key")

def _gen_key() -> str:
    import secrets
    return secrets.token_hex(16)


# ─────────────────────────────────────────────
#  CLEANUP OLD FILES
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
        "id":           vid_id,
        "title":        entry.get("title", "Unknown"),
        "channel":      entry.get("uploader") or entry.get("channel", ""),
        "duration":     int(entry.get("duration") or 0),
        "duration_fmt": _fmt_duration(entry.get("duration")),
        "views":        entry.get("view_count", 0),
        "thumbnail":    f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg",
        "url":          f"https://www.youtube.com/watch?v={vid_id}",
    }


# ─────────────────────────────────────────────
#  MASTER KEY
# ─────────────────────────────────────────────
MASTER_KEY = "aru-master-7450385463"

# ─────────────────────────────────────────────
#  COOKIES
# ─────────────────────────────────────────────
COOKIES_FILE = "cookies.txt" if os.path.exists("cookies.txt") else None

def _base_opts() -> dict:
    opts = {
        "quiet":       True,
        "no_warnings": True,
        "noplaylist":  True,
        # ✅ android_vr client — JS runtime nahi maangta, sab formats milte hain
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr"],
            }
        },
        "ffmpeg_location": _ffmpeg_exe,
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
        },
    }


# ─────────────────────────────────────────────
#  KEY MANAGEMENT
# ─────────────────────────────────────────────
@app.get("/genkey")
async def genkey(
    label: str = Query(...),
    x_api_key: str = Header(None),
):
    if x_api_key != MASTER_KEY:
        raise HTTPException(403, "Master key chahiye!")
    new_key = _gen_key()
    API_KEYS[new_key] = label
    return {"key": new_key, "label": label, "msg": "Key generate ho gayi!"}


@app.get("/keys")
async def list_keys(x_api_key: str = Header(None)):
    if x_api_key != MASTER_KEY:
        raise HTTPException(403, "Master key chahiye!")
    return {"total": len(API_KEYS), "keys": [{"key": k, "label": v} for k, v in API_KEYS.items()]}


@app.delete("/revokekey")
async def revoke_key(
    key: str = Query(...),
    x_api_key: str = Header(None),
):
    if x_api_key != MASTER_KEY:
        raise HTTPException(403, "Master key chahiye!")
    if key not in API_KEYS:
        raise HTTPException(404, "Key mili nahi!")
    label = API_KEYS.pop(key)
    return {"msg": "Key revoke ho gayi!", "label": label}


# ─────────────────────────────────────────────
#  1. SEARCH
# ─────────────────────────────────────────────
@app.get("/search")
async def search(
    query: str = Query(...),
    limit: int = Query(5, ge=1, le=10),
    x_api_key: str = Header(None),
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

    return {"query": query, "count": len(results), "results": results}


# ─────────────────────────────────────────────
#  2. INFO
# ─────────────────────────────────────────────
@app.get("/info")
async def info(
    query: str = Query(...),
    x_api_key: str = Header(None),
):
    _check_key(x_api_key)
    loop = asyncio.get_event_loop()

    is_url = query.startswith("http")
    url    = query if is_url else f"ytsearch1:{query}"
    opts   = {**_base_opts(), "extract_flat": not is_url}

    try:
        raw = await loop.run_in_executor(None, _run_ydl_no_dl, opts, url)
    except Exception as e:
        raise HTTPException(502, f"Info fetch failed: {e}")

    if not is_url and "entries" in raw:
        entries = raw.get("entries") or []
        if not entries:
            raise HTTPException(404, "No results found")
        raw = entries[0]

    return _entry_to_dict(raw)


# ─────────────────────────────────────────────
#  3. AUDIO DOWNLOAD
# ─────────────────────────────────────────────
@app.get("/audio")
async def audio(
    query: str = Query(...),
    background_tasks: BackgroundTasks = None,
    x_api_key: str = Header(None),
):
    _check_key(x_api_key)
    loop   = asyncio.get_event_loop()
    is_url = query.startswith("http")
    url    = query if is_url else f"ytsearch1:{query}"
    fid    = _short_id(query)
    out    = DOWNLOAD_DIR / f"{fid}.mp3"

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
            raise HTTPException(500, "File not created. ffmpeg issue?")

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
# ─────────────────────────────────────────────
@app.get("/video")
async def video(
    query: str = Query(...),
    quality: str = Query("720"),
    background_tasks: BackgroundTasks = None,
    x_api_key: str = Header(None),
):
    _check_key(x_api_key)
    loop   = asyncio.get_event_loop()
    is_url = query.startswith("http")
    url    = query if is_url else f"ytsearch1:{query}"
    fid    = _short_id(f"{query}_{quality}")
    out    = DOWNLOAD_DIR / f"{fid}.mp4"

    if out.exists():
        if background_tasks:
            background_tasks.add_task(cleanup_old_files)
        return FileResponse(out, media_type="video/mp4", filename=out.name)

    # ✅ Format 18 = combined mp4+audio (360p) — no merge needed, always works
    # Fallback chain: 720p merge → 480p merge → 360p combined → best available
    fmt = "18/best"

    opts = {
        **_base_opts(),
        "format":              fmt,
        "outtmpl":             str(DOWNLOAD_DIR / f"{fid}.%(ext)s"),
        "merge_output_format": "mp4",
    }

    try:
        await loop.run_in_executor(None, _run_ydl, opts, url)
    except Exception as e:
        raise HTTPException(502, f"yt-dlp failed: {e}")

    # ✅ .mp4 nahi mila toh koi bhi file dhundho (webm etc) aur rename karo
    if not out.exists():
        candidates = list(DOWNLOAD_DIR.glob(f"{fid}.*"))
        if candidates:
            candidates[0].rename(out)
        else:
            raise HTTPException(500, "Download failed.")

    if background_tasks:
        background_tasks.add_task(cleanup_old_files)

    return FileResponse(out, media_type="video/mp4", filename=out.name)


# ─────────────────────────────────────────────
#  5. STREAM
# ─────────────────────────────────────────────
@app.get("/stream")
async def stream_url(
    query:   str = Query(...),
    type:    str = Query("audio"),
    quality: str = Query("720"),
    background_tasks: BackgroundTasks = None,
    x_api_key: str = Header(None),
):
    _check_key(x_api_key)
    if type == "video":
        return await video(query=query, quality=quality, background_tasks=background_tasks)
    else:
        return await audio(query=query, background_tasks=background_tasks)

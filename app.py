import os
import re
import yt_dlp
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL  = "https://www.googleapis.com/youtube/v3/videos"


class SearchResponse(BaseModel):
    id: str
    title: str
    duration: str
    thumbnail: str
    video_url: str
    audio_url: str


def parse_duration(iso: str) -> str:
    """PT3M45S  →  3:45"""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not match:
        return "0:00"
    h, m, s = (int(x or 0) for x in match.groups())
    if h:
        return f"{h}:{m:02}:{s:02}"
    return f"{m}:{s:02}"


def get_audio_url(video_id: str) -> str:
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android"],  # android client use karo
            }
        },
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info["url"]


@app.get("/search", response_model=SearchResponse)
def search(q: str = Query(..., description="Song name to search")):
    if not YOUTUBE_API_KEY:
        raise HTTPException(status_code=500, detail="YOUTUBE_API_KEY not set.")

    # ── Step 1: Search ──────────────────────────────────────────────
    try:
        res = requests.get(YOUTUBE_SEARCH_URL, params={
            "part": "snippet",
            "q": q,
            "type": "video",
            "maxResults": 1,
            "key": YOUTUBE_API_KEY,
        }, timeout=10)
        res.raise_for_status()
        items = res.json().get("items", [])
        if not items:
            raise HTTPException(status_code=404, detail="No results found.")

        item       = items[0]
        video_id   = item["id"]["videoId"]
        title      = item["snippet"]["title"]
        thumbnail  = item["snippet"]["thumbnails"]["high"]["url"]

    except HTTPException:
        raise
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"YouTube search failed: {e}")

    # ── Step 2: Duration ────────────────────────────────────────────
    try:
        det = requests.get(YOUTUBE_VIDEO_URL, params={
            "part": "contentDetails",
            "id": video_id,
            "key": YOUTUBE_API_KEY,
        }, timeout=10)
        det.raise_for_status()
        iso_duration = det.json()["items"][0]["contentDetails"]["duration"]
        duration = parse_duration(iso_duration)

    except Exception:
        duration = "0:00"

    # ── Step 3: Audio URL via yt-dlp ────────────────────────────────
    try:
        audio_url = get_audio_url(video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio extraction failed: {e}")

    return SearchResponse(
        id=video_id,
        title=title,
        duration=duration,
        thumbnail=thumbnail,
        video_url=f"https://www.youtube.com/watch?v={video_id}",
        audio_url=audio_url,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

from flask import Flask, request, jsonify
import yt_dlp
import os
import requests
import threading
import time
import random

app = Flask(__name__)

# Keep-alive for Render
def keep_alive():
    url = os.environ.get("RENDER_URL", "")
    while True:
        time.sleep(840)
        try:
            if url:
                requests.get(url, timeout=10)
        except:
            pass

threading.Thread(target=keep_alive, daemon=True).start()

COOKIE_PATH = None

USER_AGENTS = [
    'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

# ─── Invidious fallback ───────────────────────────────────────────────────────
def get_invidious_url(video_id):
    instances = [
        "https://invidious.snopyta.org",
        "https://yewtu.be",
        "https://inv.riverside.rocks",
    ]
    for instance in instances:
        try:
            r = requests.get(f"{instance}/api/v1/videos/{video_id}", timeout=5)
            data = r.json()
            formats = data.get("adaptiveFormats", [])
            audio = next((f for f in formats if f["type"].startswith("audio/mp4")), None)
            video = next((f for f in formats if f["type"].startswith("video/mp4")), None)
            if audio or video:
                return {
                    "audio_url": audio["url"] if audio else None,
                    "video_url": video["url"] if video else None,
                }
        except:
            continue
    return None

# ─── yt-dlp se stream URLs nikalo ────────────────────────────────────────────
def get_stream(query: str):
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
        "quiet": True,
        "noplaylist": True,
        "geo_bypass": True,
        "cookiefile": COOKIE_PATH if os.path.exists(COOKIE_PATH) else None,
        "http_headers": {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["android_music", "ios"],
                "max_comments": [0],
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=False)
        track = info["entries"][0]

        formats = track.get("requested_formats")

        if formats and len(formats) >= 2:
            video_url = formats[0]["url"]
            audio_url = formats[1]["url"]
        elif formats and len(formats) == 1:
            video_url = formats[0]["url"]
            audio_url = formats[0]["url"]
        else:
            video_url = track.get("url", "")
            audio_url = track.get("url", "")

        # Agar URLs empty hain toh Invidious try karo
        if not video_url and not audio_url:
            fallback = get_invidious_url(track["id"])
            if fallback:
                video_url = fallback.get("video_url", "")
                audio_url = fallback.get("audio_url", "")

        return {
            "id": track["id"],
            "title": track["title"],
            "duration": track.get("duration", 0),
            "thumbnail": track.get("thumbnail", ""),
            "audio_url": audio_url,
            "video_url": video_url,
        }

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return {"status": "Music API running 🎵"}

@app.route("/stream")
def stream():
    query = request.args.get("query", "").strip()
    if not query:
        return {"error": "query required"}, 400

    try:
        data = get_stream(query)
        return jsonify({
            "id": data["id"],
            "title": data["title"],
            "duration": data["duration"],
            "thumbnail": data["thumbnail"],
            "audio_url": data["audio_url"],
            "video_url": data["video_url"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    app.run(host="0.0.0.0", port=port)

from flask import Flask, request, jsonify
import yt_dlp
import os
import requests
import threading
import time

app = Flask(__name__)

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

def get_stream(query: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cookies_path = os.path.join(base_dir, "cookies.txt")

    ydl_opts = {
        "quiet": True,
        "noplaylist": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["tv_embedded"],
            }
        },
    }

    if os.path.exists(cookies_path):
        ydl_opts["cookiefile"] = cookies_path

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)
        track = info["entries"][0]

        formats = track.get("formats", [])

        audio_url = None
        video_url = None

        for f in reversed(formats):
            if f.get("acodec") != "none" and f.get("url"):
                audio_url = f["url"]
                break

        for f in reversed(formats):
            if f.get("vcodec") != "none" and f.get("url"):
                video_url = f["url"]
                break

        if not audio_url:
            audio_url = formats[-1]["url"] if formats else track.get("url", "")
        if not video_url:
            video_url = audio_url

        return {
            "id": track["id"],
            "title": track["title"],
            "duration": track.get("duration", 0),
            "thumbnail": track.get("thumbnail", ""),
            "audio_url": audio_url,
            "video_url": video_url,
        }

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
        return {
            "id": data["id"],
            "title": data["title"],
            "duration": data["duration"],
            "thumbnail": data["thumbnail"],
            "audio_url": data["audio_url"],
            "video_url": data["video_url"],
        }
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    app.run(host="0.0.0.0", port=port)

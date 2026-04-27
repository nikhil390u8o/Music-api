from flask import Flask, request, jsonify
import requests
import os
import threading
import time
from urllib.parse import quote

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

INVIDIOUS = [
    "https://invidious.nerdvpn.de",
    "https://inv.nadeko.net",
    "https://invidious.privacydev.net",
]

def get_stream(query: str):
    # Search
    yt_id = None
    title = None
    duration = 0
    thumbnail = None

    for instance in INVIDIOUS:
        try:
            r = requests.get(
                f"{instance}/api/v1/search?q={quote(query)}&type=video",
                timeout=10
            )
            results = r.json()
            if results and isinstance(results, list):
                v = results[0]
                yt_id = v["videoId"]
                title = v["title"]
                duration = v.get("lengthSeconds", 0)
                thumbnail = f"https://i.ytimg.com/vi/{yt_id}/maxresdefault.jpg"
                break
        except:
            continue

    if not yt_id:
        raise Exception("Search failed")

    # Stream URLs
    audio_url = None
    video_url = None

    for instance in INVIDIOUS:
        try:
            r = requests.get(
                f"{instance}/api/v1/videos/{yt_id}",
                timeout=10
            )
            data = r.json()
            formats = data.get("adaptiveFormats", [])

            for f in formats:
                if "audio" in f.get("type", "") and not audio_url:
                    audio_url = f["url"]
                if "video" in f.get("type", "") and not video_url:
                    video_url = f["url"]

            if audio_url:
                break
        except:
            continue

    if not audio_url:
        raise Exception("Stream URL not found")

    return {
        "id": yt_id,
        "title": title,
        "duration": duration,
        "thumbnail": thumbnail,
        "audio_url": audio_url,
        "video_url": video_url or audio_url,
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
        return data
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    app.run(host="0.0.0.0", port=port)

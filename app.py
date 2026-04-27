from flask import Flask, request, jsonify
from pytubefix import YouTube, Search
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
    results = Search(query)
    yt = results.videos[0]

    audio_url = yt.streams.get_audio_only().url
    video_url = yt.streams.get_highest_resolution().url

    return {
        "id": yt.video_id,
        "title": yt.title,
        "duration": yt.length,
        "thumbnail": yt.thumbnail_url,
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

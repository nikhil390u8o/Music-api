from flask import Flask, request, jsonify
import requests
import os
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
    # Step 1: Search
    search_r = requests.get(
        f"https://pipedapi.kavin.rocks/search?q={query}&filter=music_songs",
        timeout=15
    )
    items = search_r.json().get("items", [])
    if not items:
        raise Exception("No results found")
    
    item = items[0]
    yt_id = item["url"].split("?v=")[-1]
    title = item["title"]
    duration = item.get("duration", 0)
    thumbnail = item.get("thumbnail", f"https://i.ytimg.com/vi/{yt_id}/maxresdefault.jpg")

    # Step 2: Stream URL from Piped
    stream_r = requests.get(
        f"https://pipedapi.kavin.rocks/streams/{yt_id}",
        timeout=15
    )
    data = stream_r.json()
    
    audio_url = None
    video_url = None

    for s in data.get("audioStreams", []):
        if s.get("url"):
            audio_url = s["url"]
            break

    for s in data.get("videoStreams", []):
        if s.get("url"):
            video_url = s["url"]
            break

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

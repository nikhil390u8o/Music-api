from flask import Flask, request, jsonify
import os
import requests
import threading
import time

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

# ─── Piped Instances ──────────────────────────────────────────────────────────
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://piped-api.garudalinux.org",
    "https://api.piped.projectsegfau.lt",
    "https://pipedapi.leptons.xyz",
]

# ─── Search YouTube via Piped ─────────────────────────────────────────────────
def search_piped(query):
    for instance in PIPED_INSTANCES:
        try:
            r = requests.get(
                f"{instance}/search",
                params={"q": query, "filter": "music_songs"},
                timeout=5
            )
            results = r.json().get("items", [])
            if results:
                video_id = results[0]["url"].split("?v=")[-1]
                return video_id
        except:
            continue
    return None

# ─── Get Streams via Piped ────────────────────────────────────────────────────
def get_piped_streams(video_id):
    for instance in PIPED_INSTANCES:
        try:
            r = requests.get(f"{instance}/streams/{video_id}", timeout=5)
            data = r.json()

            # Video URL - best mp4
            video_streams = data.get("videoStreams", [])
            video_url = next(
                (s["url"] for s in video_streams if s.get("mimeType", "").startswith("video/mp4")),
                None
            )

            # Audio URL - best mp4
            audio_streams = data.get("audioStreams", [])
            audio_url = next(
                (s["url"] for s in audio_streams if s.get("mimeType", "").startswith("audio/mp4")),
                None
            )

            if video_url or audio_url:
                return {
                    "title": data.get("title", "Unknown"),
                    "duration": data.get("duration", 0),
                    "thumbnail": data.get("thumbnailUrl", ""),
                    "video_url": video_url or audio_url,
                    "audio_url": audio_url or video_url,
                }
        except:
            continue
    return None

# ─── Main Function ────────────────────────────────────────────────────────────
def get_stream(query: str):
    video_id = search_piped(query)
    if not video_id:
        raise Exception("No results found")

    data = get_piped_streams(video_id)
    if not data:
        raise Exception("Could not get stream URLs")

    return {
        "id": video_id,
        "title": data["title"],
        "duration": data["duration"],
        "thumbnail": data["thumbnail"],
        "audio_url": data["audio_url"],
        "video_url": data["video_url"],
    }

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return {"status": "Music API running 🎵"}

@app.route("/stream")
def stream():
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify({"error": "query required"}), 400

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

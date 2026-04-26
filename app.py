from flask import Flask, request, jsonify
import yt_dlp
import os
import tempfile
import base64

app = Flask(__name__)

# ---------- Load cookies from BASE64 ENV ----------
COOKIES_FILE = None
b64 = os.environ.get("YT_COOKIES_B64")

if b64:
    decoded = base64.b64decode(b64).decode("utf-8")
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    tmp.write(decoded)
    tmp.flush()
    tmp.close()
    COOKIES_FILE = tmp.name


# ---------- Search YouTube video page ----------
def search_video(query: str) -> str:
    ydl_opts = {
        "quiet": True,
        "noplaylist": True,
        "geo_bypass": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=False)
        return info["entries"][0]["webpage_url"]


# ---------- Extract Audio & Video streams ----------
def extract_streams(page_url: str):
    common_opts = {
        "quiet": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,
    }

    if COOKIES_FILE:
        common_opts["cookiefile"] = COOKIES_FILE

    # ---- VIDEO (mp4 with audio) ----
    video_opts = common_opts.copy()
    video_opts["format"] = "best[ext=mp4]/best"

    with yt_dlp.YoutubeDL(video_opts) as ydl:
        info_video = ydl.extract_info(page_url, download=False)
        video_url = info_video["url"]

    # ---- AUDIO (m4a) ----
    audio_opts = common_opts.copy()
    audio_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"

    with yt_dlp.YoutubeDL(audio_opts) as ydl:
        info_audio = ydl.extract_info(page_url, download=False)
        audio_url = info_audio["url"]

    return {
        "id": info_video["id"],
        "title": info_video["title"],
        "duration": info_video.get("duration", 0),
        "thumbnail": info_video.get("thumbnail", ""),
        "audio_url": audio_url,
        "video_url": video_url,
    }


# ---------- Routes ----------
@app.route("/")
def index():
    return {"status": "Music API running 🎵"}


@app.route("/stream")
def stream():
    query = request.args.get("query", "").strip()
    if not query:
        return {"error": "query required"}, 400

    try:
        page_url = search_video(query)
        data = extract_streams(page_url)
        return jsonify(data)
    except Exception as e:
        return {"error": str(e)}, 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    app.run(host="0.0.0.0", port=port)

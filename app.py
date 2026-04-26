from flask import Flask, request, jsonify
import yt_dlp
import os
import tempfile

app = Flask(__name__)

# ---- Cookies file once ----
COOKIES_FILE = None
cookies_content = os.environ.get("YT_COOKIES", "")

if cookies_content:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    tmp.write(cookies_content)
    tmp.flush()
    tmp.close()
    COOKIES_FILE = tmp.name


def search_video(query: str) -> str:
    ydl_opts = {
        "quiet": True,
        "noplaylist": True,
        "geo_bypass": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=False)
        return info["entries"][0]["webpage_url"]


def extract_streams(video_url: str):
    ydl_opts = {
        "quiet": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    }

    if COOKIES_FILE:
        ydl_opts["cookiefile"] = COOKIES_FILE

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

        audio_url = None
        video_url = None

        # yt_dlp jab format select karta hai, final url yaha milta hai
        if "url" in info:
            video_url = info["url"]

        # bestaudio alag se nikalte hain
        ydl_opts_audio = ydl_opts.copy()
        ydl_opts_audio["format"] = "bestaudio[ext=m4a]/bestaudio/best"

        with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl2:
            info_audio = ydl2.extract_info(video_url, download=False)
            audio_url = info_audio["url"]

        return {
            "id": info["id"],
            "title": info["title"],
            "duration": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
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
        video_page = search_video(query)
        data = extract_streams(video_page)
        return jsonify(data)
    except Exception as e:
        return {"error": str(e)}, 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    app.run(host="0.0.0.0", port=port)

from fastapi import FastAPI, HTTPException
import yt_dlp
import os

app = FastAPI()

# Cookies file ka path
COOKIE_PATH = "cookies.txt"

def get_stream_url(query):
    ydl_opts = {
        'format': 'best[ext=mp4]/best',  # ✅ Force MP4 (always has URL)
        'quiet': True,
        'noplaylist': True,
        'cookiefile': COOKIE_PATH if os.path.exists(COOKIE_PATH) else None,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            
            # ✅ This will ALWAYS have a URL because we forced mp4 format
            stream_url = info.get('url')
            
            if not stream_url:
                raise Exception("No stream URL found")
            
            return {
                "title": info.get('title'),
                "url": stream_url,
                "status": "success"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


@app.get("/play")
async def play(song: str):
    data = get_stream_url(song)
    if data["status"] == "success":
        return data
    raise HTTPException(status_code=400, detail=data["message"])

@app.get("/")
def home():
    return {"status": "API is Running with Cookies Support"}

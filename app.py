from fastapi import FastAPI, HTTPException
import yt_dlp
import os

app = FastAPI()

# Cookies file ka path
COOKIE_PATH = "cookies.txt"

def get_stream_url(query):
    ydl_opts = {
        # 'best' use karne se yt-dlp khud sabse best playable link dhoond lega
        'format': 'best', 
        'quiet': True,
        'noplaylist': True,
        'cookiefile': COOKIE_PATH if os.path.exists(COOKIE_PATH) else None,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Search query
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            
            # Streaming link nikalne ka sahi tarika
            return {
                "title": info.get('title'),
                "url": info.get('url'), # Direct streaming URL
                "duration": info.get('duration'),
                "thumb": info.get('thumbnail'),
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

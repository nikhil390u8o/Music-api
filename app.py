from fastapi import FastAPI, HTTPException
import yt_dlp
import os

app = FastAPI()

# Cookies file ka path
COOKIE_PATH = "cookies.txt"

def get_stream_url(query):
    ydl_opts = {
        # 'best' likhne se wo playable format khud dhoond lega
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,
        'noplaylist': True,
        'cookiefile': COOKIE_PATH if os.path.exists(COOKIE_PATH) else None,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Search query se video info fetch karein
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            
            # Agar format availability ka issue ho toh is tarah URL nikalte hain
            return {
                "title": info.get('title'),
                "url": info.get('url'),  # Direct streaming link
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

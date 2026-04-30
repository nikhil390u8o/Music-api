import yt_dlp
import os
from fastapi import FastAPI, HTTPException

app = FastAPI()
COOKIE_PATH = "cookies.txt"

def get_stream_url(query):
    ydl_opts = {
        # 'best' ki jagah 0 (zero) use karein, ye bina check kiye link nikalta hai
        'format': 'best', 
        'quiet': True,
        'noplaylist': True,
        'cookiefile': COOKIE_PATH if os.path.exists(COOKIE_PATH) else None,
        # Sabse important: Ye do lines YouTube check bypass karti hain
        'youtube_include_dash_manifest': False,
        'youtube_include_hls_manifest': True,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Search logic
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            
            # Agar best format na mile, toh list mein se koi bhi playable uthao
            url = info.get('url')
            if not url:
                # Fallback to direct stream link
                for f in info.get('formats', []):
                    if f.get('acodec') != 'none' and f.get('vcodec') != 'none':
                        url = f.get('url')
                        break

            return {
                "title": info.get('title'),
                "url": url,
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
    return {"status": "Running"}

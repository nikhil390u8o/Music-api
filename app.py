import yt_dlp
import os
from fastapi import FastAPI, HTTPException

app = FastAPI()
COOKIE_PATH = "cookies.txt"

def get_stream_url(query):
    ydl_opts = {
        # Format ko bilkul open chhod diya taaki error na aaye
        'format': 'best', 
        'quiet': True,
        'noplaylist': True,
        'cookiefile': COOKIE_PATH if os.path.exists(COOKIE_PATH) else None,
        # Ye line YouTube ke naya security check bypass karti hai
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'logtostderr': False,
        'geo_bypass': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Info extract karein bina format check kiye
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if not info or 'entries' not in info or not info['entries']:
                return {"status": "error", "message": "Video not found or IP Blocked"}
                
            video_data = info['entries'][0]
            
            return {
                "title": video_data.get('title'),
                "url": video_data.get('url'), # Direct Stream URL
                "status": "success"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

@app.get("/play")
async def play(song: str):
    data = get_stream_url(song)
    if data["status"] == "success" and data["url"]:
        return data
    # Agar format error phir bhi aaye toh manual message
    raise HTTPException(status_code=400, detail="YouTube blocked the request. Try refreshing cookies.txt")

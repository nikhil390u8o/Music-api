import yt_dlp
import os
from fastapi import FastAPI, HTTPException

app = FastAPI()
COOKIE_PATH = "cookies.txt"

def get_stream_url(query):
    # Format line ko poori tarah hata diya hai taaki error na aaye
    ydl_opts = {
    # ID 18 sabse pehle (360p mp4 with audio), agar wo na mile to best dhoondo
    'format': '18/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
    'quiet': True,
    'noplaylist': True,
    'cookiefile': 'cookies.txt',
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
}

    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Search query se video info fetch karein
            search_result = ydl.extract_info(f"ytsearch:{query}", download=False)
            if not search_result['entries']:
                return {"status": "error", "message": "No video found"}
                
            info = search_result['entries'][0]
            
            # Agar direct URL na mile, toh formats list mein se pehla uthao
            formats = info.get('formats', [])
            # Hum wo format dhoondenge jisme audio aur video dono ho
            url = info.get('url')
            if not url and formats:
                url = formats[-1].get('url') # Last format aksar best hota hai

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

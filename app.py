from fastapi import FastAPI, HTTPException
import yt_dlp
import os

app = FastAPI()

# Cookies file ka path
COOKIE_PATH = "cookies.txt"

def get_stream_url(query):
    ydl_opts = {
        'format': 'bestaudio+bestvideo/best',  # ✅ This is correct
        'quiet': True,
        'noplaylist': True,
        'cookiefile': COOKIE_PATH if os.path.exists(COOKIE_PATH) else None,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            
            # ✅ FIX: Get the actual streaming URL
            # Method 1: If format is already merged
            stream_url = info.get('url')
            
            # Method 2: If url is None (happens with separate formats)
            if not stream_url and 'formats' in info:
                # Get the best format that has a direct URL
                for f in info['formats']:
                    if f.get('url') and f.get('vcodec') != 'none':
                        stream_url = f.get('url')
                        break
                
                # If still none, just take any format with URL
                if not stream_url:
                    stream_url = info['formats'][0].get('url') if info['formats'] else None
            
            # ✅ Method 3: Force yt-dlp to give a direct playable URL
            if not stream_url:
                # Re-extract with different options
                ydl_opts2 = {
                    'format': 'best[ext=mp4]/best',  # Force mp4 format
                    'quiet': True,
                    'noplaylist': True,
                    'cookiefile': COOKIE_PATH if os.path.exists(COOKIE_PATH) else None,
                }
                with yt_dlp.YoutubeDL(ydl_opts2) as ydl2:
                    info2 = ydl2.extract_info(info['webpage_url'], download=False)
                    stream_url = info2.get('url')
            
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

import yt_dlp
import os
from fastapi import FastAPI, HTTPException

app = FastAPI()
COOKIE_PATH = "cookies.txt"

def get_stream_url(query):
    # Sabse minimal options taki YouTube ko shaq na ho
    ydl_opts = {
        'format': 'bestaudio/best', # Sirf audio ya best, koi ext=mp4 ki zidd nahi
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'cookiefile': COOKIE_PATH if os.path.exists(COOKIE_PATH) else None,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Step 1: Search karke info nikaalo
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if not info or 'entries' not in info or not info['entries']:
                return {"status": "error", "message": "Video not found"}
                
            video_data = info['entries'][0]
            
            # Step 2: Sabse pehla playable link uthao jo available ho
            # Hum format ID check hi nahi karenge
            formats = video_data.get('formats', [video_data])
            url = None
            
            # Pehle direct url check karo, nahi toh formats list scan karo
            if video_data.get('url'):
                url = video_data['url']
            else:
                for f in formats:
                    if f.get('url'):
                        url = f['url']
                        break

            if not url:
                return {"status": "error", "message": "No streamable URL found"}

            return {
                "title": video_data.get('title'),
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

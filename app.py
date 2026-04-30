import yt_dlp
import os
from fastapi import FastAPI, HTTPException

app = FastAPI()
COOKIE_PATH = "cookies.txt"

def get_stream_url(query):
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'noplaylist': True,
        'cookiefile': COOKIE_PATH if os.path.exists(COOKIE_PATH) else None,
        # YE HAI ASLI JUGAD: YouTube Android client pretend karna
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
                'skip': ['dash', 'hls']
            }
        },
        'user_agent': 'com.google.android.youtube/19.11.38 (Linux; U; Android 11; en_US; SM-G991B Build/RP1A.200720.012)'
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if not info or 'entries' not in info or not info['entries']:
                return {"status": "error", "message": "Search Failed"}
                
            video_data = info['entries'][0]
            
            # Agar best format hide ho gaya ho, toh formats list scan karein
            url = video_data.get('url')
            if not url:
                for f in video_data.get('formats', []):
                    if f.get('url'):
                        url = f.get('url')
                        break

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
    if data["status"] == "success" and data["url"]:
        return data
    raise HTTPException(status_code=400, detail=data["message"])

from fastapi import FastAPI, HTTPException
import yt_dlp
import os

app = FastAPI()

# Cookies file ka path
COOKIE_PATH = "cookies.txt"

def get_stream_url(query):
    ydl_opts = {
        # 'best' hatakar sirf 0 ya direct link ka use karein
        'format': 'bestaudio+bestvideo/best', 
        'quiet': True,
        'noplaylist': True,
        'cookiefile': COOKIE_PATH if os.path.exists(COOKIE_PATH) else None,
        # Ye headers YouTube ko bewakoof banane ke liye hain
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            
            # Streaming link nikalne ka fix
            return {
                "title": info.get('title'),
                "url": info.get('url'), # Agar yahan error aaye to niche wala try karo
                "status": "success"
            }
        except Exception as e:
            # Agar format ka fir bhi panga kare, to ye fallback use hoga
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

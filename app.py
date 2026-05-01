import os
import json
import asyncio
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import aiohttp
from urllib.parse import quote, unquote
import re

app = FastAPI(title="Unrestricted Music Stream API", version="1.0")

# CORS setup for unrestricted access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom headers to bypass restrictions
BYPASS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.youtube.com/",
    "Origin": "https://www.youtube.com",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site"
}

class YouTubeStreamer:
    def __init__(self):
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': False,
            'ignoreerrors': True,
            'no_color': True,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'http_headers': BYPASS_HEADERS,
        }
    
    async def search(self, query: str, limit: int = 10):
        """Search YouTube without restrictions"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Bypass search restrictions
                search_query = f"ytsearch{limit}:{query}"
                info = ydl.extract_info(search_query, download=False)
                
                if not info or 'entries' not in info:
                    return []
                
                results = []
                for entry in info['entries']:
                    if entry:
                        # Get streaming URLs
                        stream_info = await self.get_stream_urls(entry['id'])
                        results.append({
                            "id": entry.get('id'),
                            "title": entry.get('title', 'Unknown'),
                            "thumbnail": entry.get('thumbnail', f"https://i.ytimg.com/vi/{entry['id']}/hqdefault.jpg"),
                            "duration": entry.get('duration', 0),
                            "author": entry.get('uploader', 'Unknown'),
                            "audio": stream_info.get('audio'),
                            "video": stream_info.get('video')
                        })
                return results
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    async def get_stream_urls(self, video_id: str):
        """Extract direct streaming URLs with bypass"""
        try:
            ydl_opts_stream = {
                **self.ydl_opts,
                'format': 'bestaudio+bestvideo/best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts_stream) as ydl:
                url = f"https://www.youtube.com/watch?v={video_id}"
                info = ydl.extract_info(url, download=False)
                
                audio_url = None
                video_url = None
                
                # Extract best audio
                if 'formats' in info:
                    for fmt in info['formats']:
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                            if 'url' in fmt:
                                audio_url = fmt['url']
                                break
                    
                    # Extract best video (with audio)
                    for fmt in info['formats']:
                        if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                            if 'url' in fmt:
                                video_url = fmt['url']
                                break
                
                return {"audio": audio_url, "video": video_url}
        except Exception as e:
            print(f"Stream extraction error: {e}")
            return {"audio": None, "video": None}

streamer = YouTubeStreamer()

@app.get("/")
async def root():
    return {"status": "active", "message": "Unrestricted Streaming API", "endpoints": ["/search", "/stream", "/direct"]}

@app.get("/search")
async def search_songs(q: str = Query(..., min_length=1), limit: int = Query(5, ge=1, le=50)):
    """Search endpoint - returns streaming URLs directly"""
    if not q or q.strip() == "":
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    results = await streamer.search(q, limit)
    
    return {
        "query": q,
        "count": len(results),
        "results": results
    }

@app.get("/stream/{video_id}")
async def stream_audio(video_id: str, format: str = "audio"):
    """Direct streaming endpoint"""
    try:
        stream_info = await streamer.get_stream_urls(video_id)
        
        if format == "audio" and stream_info.get("audio"):
            url = stream_info["audio"]
        elif format == "video" and stream_info.get("video"):
            url = stream_info["video"]
        else:
            raise HTTPException(status_code=404, detail="Stream not available")
        
        # Proxy the stream with bypass headers
        async with aiohttp.ClientSession(headers=BYPASS_HEADERS) as session:
            async with session.get(url, headers=BYPASS_HEADERS) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail="Stream fetch failed")
                
                return StreamingResponse(
                    response.content.iter_chunked(8192),
                    media_type="audio/mpeg" if format == "audio" else "video/mp4",
                    headers={
                        "Content-Type": "audio/mpeg" if format == "audio" else "video/mp4",
                        "Accept-Ranges": "bytes",
                        "Content-Disposition": f'inline; filename="stream.{format}"'
                    }
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/direct")
async def direct_stream(q: str = Query(...)):
    """One-click direct streaming - returns first result's stream"""
    results = await streamer.search(q, 1)
    
    if not results:
        raise HTTPException(status_code=404, detail="No results found")
    
    first_result = results[0]
    
    # Get fresh streaming URLs
    stream_info = await streamer.get_stream_urls(first_result["id"])
    
    return {
        "id": first_result["id"],
        "title": first_result["title"],
        "audio": stream_info.get("audio"),
        "video": stream_info.get("video"),
        "direct_endpoints": {
            "audio": f"/stream/{first_result['id']}?format=audio",
            "video": f"/stream/{first_result['id']}?format=video"
        }
    }

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "bypass": "active"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)

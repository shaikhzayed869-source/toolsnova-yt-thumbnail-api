from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from youtube_transcript_api import YouTubeTranscriptApi
import re

app = FastAPI()

# Allow your website to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://toolsnova.github.io"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

def extract_video_id(url: str) -> str:
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([\w-]+)',
        r'(?:youtu\.be\/)([\w-]+)',
        r'(?:youtube\.com\/embed\/)([\w-]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise HTTPException(400, "Invalid YouTube URL")

QUALITIES = ["default", "mqdefault", "hqdefault", "sddefault", "maxresdefault"]

@app.get("/api/thumbnail")
async def get_thumbnail(url: str = Query(...), quality: str = "maxresdefault"):
    try:
        video_id = extract_video_id(url)
        if quality not in QUALITIES:
            return JSONResponse({"error": f"Invalid quality. Use: {QUALITIES}"}, status_code=400)
        
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
        return {
            "success": True,
            "video_id": video_id,
            "quality": quality,
            "thumbnail_url": thumbnail_url
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.get("/api/transcript")
async def get_transcript(url: str = Query(...), language: str = "en"):
    try:
        video_id = extract_video_id(url)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to get transcript
        transcript = None
        try:
            transcript = transcript_list.find_transcript([language])
        except:
            try:
                transcript = transcript_list.find_generated_transcript([language])
            except:
                transcript = next(iter(transcript_list))
        
        segments = transcript.fetch()
        full_text = " ".join([entry['text'] for entry in segments])
        
        return {
            "success": True,
            "video_id": video_id,
            "language": transcript.language,
            "transcript": full_text,
            "segments": segments[:20]  # First 20 segments only
        }
    except Exception as e:
        return JSONResponse({"error": f"No transcript available: {str(e)}"}, status_code=404)

@app.get("/")
async def root():
    return {"message": "ToolsNova API is running!", "endpoints": ["/api/thumbnail", "/api/transcript"]}
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import re

app = FastAPI(title="ToolsNova Thumbnail API", version="1.0.0")

# Allow your website to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://toolsnova.github.io",
        "https://*.github.io",
        "http://localhost:3000",
        "http://localhost:5500",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([\w-]+)',
        r'(?:youtu\.be\/)([\w-]+)',
        r'(?:youtube\.com\/embed\/)([\w-]+)',
        r'(?:youtube\.com\/shorts\/)([\w-]+)',
        r'(?:youtube\.com\/v\/)([\w-]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise HTTPException(400, "Invalid YouTube URL")

QUALITIES = ["default", "mqdefault", "hqdefault", "sddefault", "maxresdefault"]

QUALITY_NAMES = {
    "default": "Default (120x90)",
    "mqdefault": "Medium Quality (320x180)",
    "hqdefault": "High Quality (480x360)",
    "sddefault": "SD Quality (640x480)",
    "maxresdefault": "Max Resolution (1920x1080)"
}

@app.get("/api/thumbnail")
async def get_thumbnail(
    url: str = Query(..., description="YouTube video URL"),
    quality: str = Query("maxresdefault", description=f"Quality option: {', '.join(QUALITIES)}")
):
    """Get YouTube thumbnail URL with multiple quality options"""
    try:
        video_id = extract_video_id(url)
        
        if quality not in QUALITIES:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "INVALID_QUALITY",
                    "message": f"Invalid quality. Use: {', '.join(QUALITIES)}",
                    "available_qualities": QUALITIES
                }
            )
        
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
        
        return {
            "success": True,
            "video_id": video_id,
            "quality": quality,
            "quality_name": QUALITY_NAMES.get(quality, quality),
            "thumbnail_url": thumbnail_url,
            "download_url": thumbnail_url
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "INVALID_URL",
                "message": "Invalid YouTube URL. Please check and try again."
            }
        )

@app.get("/api/thumbnail/all")
async def get_all_thumbnails(url: str = Query(..., description="YouTube video URL")):
    """Get all available thumbnail qualities at once"""
    try:
        video_id = extract_video_id(url)
        
        thumbnails = {}
        for quality in QUALITIES:
            thumbnails[quality] = {
                "url": f"https://img.youtube.com/vi/{video_id}/{quality}.jpg",
                "quality": quality,
                "name": QUALITY_NAMES.get(quality, quality)
            }
        
        return {
            "success": True,
            "video_id": video_id,
            "thumbnails": thumbnails
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "INVALID_URL",
                "message": "Invalid YouTube URL. Please check and try again."
            }
        )

@app.get("/")
async def root():
    return {
        "message": "ToolsNova Thumbnail API is running!",
        "version": "1.0.0",
        "endpoints": [
            "/api/thumbnail?url=YOUTUBE_URL&quality=QUALITY",
            "/api/thumbnail/all?url=YOUTUBE_URL"
        ],
        "qualities": QUALITY_NAMES,
        "documentation": "/docs",
        "status": "operational"
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ToolsNova Thumbnail API",
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }
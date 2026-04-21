from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable
)
import re
from typing import Optional, List

app = FastAPI(title="ToolsNova YouTube API", version="2.0.0")

# Allow your website to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://toolsnova.github.io",
        "https://*.github.io",
        "http://localhost:3000",  # For local testing
        "http://localhost:5500",  # For live server testing
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

# List of language codes to try (in order of preference)
LANGUAGE_CODES = [
    'en',    # English
    'hi',    # Hindi
    'es',    # Spanish
    'fr',    # French
    'de',    # German
    'ja',    # Japanese
    'ko',    # Korean
    'pt',    # Portuguese
    'ru',    # Russian
    'ar',    # Arabic
    'bn',    # Bengali
    'pa',    # Punjabi
    'ta',    # Tamil
    'te',    # Telugu
    'mr',    # Marathi
    'gu',    # Gujarati
    'kn',    # Kannada
    'ml',    # Malayalam
]

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
                    "message": f"Invalid quality. Use: {', '.join(QUALITIES)}"
                }
            )
        
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
        
        # Get video title and info (optional - requires additional API call)
        return {
            "success": True,
            "video_id": video_id,
            "quality": quality,
            "thumbnail_url": thumbnail_url,
            "download_url": thumbnail_url,
            "qualities_available": QUALITIES
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
                "quality": quality
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

@app.get("/api/transcript")
async def get_transcript(
    url: str = Query(..., description="YouTube video URL"),
    language: Optional[str] = Query(None, description="Preferred language code (e.g., 'en', 'hi', 'es')")
):
    """
    Get YouTube video transcript/subtitles.
    Automatically tries multiple languages and fallback options.
    """
    try:
        video_id = extract_video_id(url)
        
        # Get available transcripts
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        except VideoUnavailable:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "VIDEO_UNAVAILABLE",
                    "message": "Video is unavailable or private."
                }
            )
        except TranscriptsDisabled:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "TRANSCRIPTS_DISABLED",
                    "message": "This video has transcripts/subtitles disabled by the creator."
                }
            )
        
        # Strategy 1: Try requested language if specified
        if language:
            try:
                transcript = transcript_list.find_transcript([language])
                segments = transcript.fetch()
                return format_success_response(video_id, transcript, segments)
            except NoTranscriptFound:
                pass  # Continue to fallback strategies
        
        # Strategy 2: Try common languages in order
        for lang in LANGUAGE_CODES:
            try:
                transcript = transcript_list.find_transcript([lang])
                segments = transcript.fetch()
                return format_success_response(video_id, transcript, segments)
            except NoTranscriptFound:
                continue
        
        # Strategy 3: Try auto-generated captions (any language)
        try:
            auto_transcripts = transcript_list._generate_transcripts
            if auto_transcripts:
                # Get the first available auto-generated transcript
                first_lang = list(auto_transcripts.keys())[0]
                transcript = auto_transcripts[first_lang]
                segments = transcript.fetch()
                return format_success_response(video_id, transcript, segments)
        except:
            pass
        
        # Strategy 4: Get any manually added transcript
        try:
            for transcript_obj in transcript_list:
                if not transcript_obj.is_generated:
                    segments = transcript_obj.fetch()
                    return format_success_response(video_id, transcript_obj, segments)
        except:
            pass
        
        # Strategy 5: Get ANY transcript (last resort)
        try:
            for transcript_obj in transcript_list:
                segments = transcript_obj.fetch()
                return format_success_response(video_id, transcript_obj, segments)
        except:
            pass
        
        # No transcript found at all
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": "NO_TRANSCRIPT_AVAILABLE",
                "message": "No transcript or subtitles found for this video. Try a different video."
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later."
            }
        )

def format_success_response(video_id: str, transcript, segments):
    """Format successful transcript response"""
    # Join all text segments
    full_text = " ".join([segment['text'] for segment in segments])
    
    # Add timestamps for each segment
    formatted_segments = []
    for segment in segments[:100]:  # Limit to first 100 segments for performance
        formatted_segments.append({
            "text": segment['text'],
            "start": segment['start'],
            "duration": segment['duration'],
            "start_formatted": format_time(segment['start'])
        })
    
    return {
        "success": True,
        "video_id": video_id,
        "language": transcript.language,
        "language_code": transcript.language_code,
        "is_generated": transcript.is_generated,
        "transcript": full_text,
        "transcript_length": len(full_text),
        "word_count": len(full_text.split()),
        "segment_count": len(segments),
        "segments": formatted_segments
    }

def format_time(seconds: float) -> str:
    """Convert seconds to MM:SS format"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

@app.get("/api/transcript/srt")
async def get_transcript_srt(
    url: str = Query(..., description="YouTube video URL"),
    language: Optional[str] = Query(None, description="Preferred language code")
):
    """Get transcript in SRT subtitle format"""
    try:
        video_id = extract_video_id(url)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to find transcript (same logic as above)
        transcript = None
        if language:
            try:
                transcript = transcript_list.find_transcript([language])
            except:
                pass
        
        if not transcript:
            for lang in LANGUAGE_CODES[:5]:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    break
                except:
                    continue
        
        if not transcript:
            transcript = next(iter(transcript_list))
        
        segments = transcript.fetch()
        
        # Generate SRT content
        srt_content = ""
        for i, segment in enumerate(segments, 1):
            start = format_srt_time(segment['start'])
            end = format_srt_time(segment['start'] + segment['duration'])
            srt_content += f"{i}\n{start} --> {end}\n{segment['text']}\n\n"
        
        return JSONResponse(
            content={
                "success": True,
                "video_id": video_id,
                "language": transcript.language,
                "srt": srt_content
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": "SRT_NOT_AVAILABLE",
                "message": "Cannot generate SRT for this video."
            }
        )

def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

@app.get("/api/transcript/info")
async def get_transcript_info(url: str = Query(..., description="YouTube video URL")):
    """Get information about available transcripts for a video without fetching content"""
    try:
        video_id = extract_video_id(url)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        available_transcripts = []
        for transcript in transcript_list:
            available_transcripts.append({
                "language": transcript.language,
                "language_code": transcript.language_code,
                "is_generated": transcript.is_generated,
                "is_translatable": transcript.is_translatable
            })
        
        return {
            "success": True,
            "video_id": video_id,
            "available_transcripts": available_transcripts,
            "transcript_count": len(available_transcripts)
        }
    except Exception as e:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": "NO_TRANSCRIPTS",
                "message": "No transcripts available for this video."
            }
        )

@app.get("/")
async def root():
    return {
        "message": "ToolsNova YouTube API is running!",
        "version": "2.0.0",
        "endpoints": [
            "/api/thumbnail - Get YouTube thumbnail",
            "/api/thumbnail/all - Get all thumbnail qualities",
            "/api/transcript - Get video transcript",
            "/api/transcript/srt - Get transcript as SRT",
            "/api/transcript/info - Check available transcripts"
        ],
        "documentation": "/docs",
        "status": "operational"
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ToolsNova API",
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }
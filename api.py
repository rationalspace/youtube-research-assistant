#!/usr/bin/env python3
"""
FastAPI Server for YouTube Research Assistant
Provides API endpoints to query research.db and trigger video processing
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import sqlite3
import os

from db_manager import search_videos, get_stats, DB_PATH

app = FastAPI(
    title="YouTube Research Assistant API",
    description="Query video summaries and trigger processing",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background task tracking
processing_status = {
    "is_processing": False,
    "last_run": None,
    "last_result": None
}


def run_youtube_monitor():
    """Background task to run youtube_monitor.py"""
    global processing_status
    
    processing_status["is_processing"] = True
    processing_status["last_run"] = datetime.now().isoformat()
    
    try:
        # Run the monitor script
        result = subprocess.run(
            ["python", "check_once.py"],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        processing_status["last_result"] = {
            "success": result.returncode == 0,
            "stdout": result.stdout[-1000:] if result.stdout else "",  # Last 1000 chars
            "stderr": result.stderr[-1000:] if result.stderr else "",
            "return_code": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        processing_status["last_result"] = {
            "success": False,
            "error": "Processing timeout (30 minutes exceeded)"
        }
    except Exception as e:
        processing_status["last_result"] = {
            "success": False,
            "error": str(e)
        }
    finally:
        processing_status["is_processing"] = False


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "YouTube Research Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "ask": "/ask?q=<query>&days=<days>",
            "digest": "/digest?days=<days>",
            "ingest": "POST /ingest",
            "status": "/status",
            "stats": "/stats"
        }
    }


@app.get("/ask")
async def ask(
    q: str = Query(..., description="Search query"),
    days: Optional[int] = Query(None, description="Filter videos from last N days"),
    limit: int = Query(10, description="Maximum results", ge=1, le=100)
):
    """
    Semantic keyword search across video summaries.
    
    Searches video titles, summaries, topics, recommendations, and action items.
    
    Example: /ask?q=TSLA&days=7&limit=5
    """
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="Database not found. Run /ingest first.")
    
    # Calculate from_date if days parameter provided
    from_date = None
    if days:
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    try:
        results = search_videos(
            search_term=q,
            from_date=from_date,
            limit=limit
        )
        
        # Format results
        formatted_results = []
        for video in results:
            formatted_results.append({
                "video_id": video['video_id'],
                "title": video['video_title'],
                "channel": video['channel_name'],
                "url": video['video_url'],
                "published": video['published_date'],
                "duration": video.get('duration_seconds', 0),
                "source_type": video['source_type'],
                "summary": video['summary_text'],
                "key_topics": video.get('key_topics'),
                "recommendations": video.get('recommendations'),
                "action_items": video.get('action_items')
            })
        
        return {
            "query": q,
            "days": days,
            "from_date": from_date,
            "count": len(formatted_results),
            "results": formatted_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/digest")
async def digest(
    days: int = Query(7, description="Number of days to include", ge=1, le=90)
):
    """
    Get a structured digest of recent videos.
    
    Returns videos from the last N days, grouped by channel with summaries.
    
    Example: /digest?days=7
    """
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="Database not found. Run /ingest first.")
    
    from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    try:
        # Get all videos from the time period
        results = search_videos(
            from_date=from_date,
            limit=100  # Get up to 100 videos
        )
        
        # Group by channel
        by_channel = {}
        for video in results:
            channel = video['channel_name']
            if channel not in by_channel:
                by_channel[channel] = []
            
            by_channel[channel].append({
                "video_id": video['video_id'],
                "title": video['video_title'],
                "url": video['video_url'],
                "published": video['published_date'],
                "duration": video.get('duration_seconds', 0),
                "source_type": video['source_type'],
                "summary": video['summary_text'],
                "key_topics": video.get('key_topics'),
                "recommendations": video.get('recommendations'),
                "action_items": video.get('action_items')
            })
        
        # Sort channels by number of videos
        sorted_channels = sorted(
            by_channel.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        digest_data = {
            "period": {
                "days": days,
                "from": from_date,
                "to": datetime.now().strftime('%Y-%m-%d')
            },
            "summary": {
                "total_videos": len(results),
                "total_channels": len(by_channel),
                "channels": [
                    {
                        "name": channel,
                        "video_count": len(videos)
                    }
                    for channel, videos in sorted_channels
                ]
            },
            "videos_by_channel": {
                channel: videos
                for channel, videos in sorted_channels
            }
        }
        
        return digest_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Digest generation failed: {str(e)}")


@app.post("/ingest")
async def ingest(background_tasks: BackgroundTasks):
    """
    Trigger the YouTube monitoring pipeline.
    
    Runs check_once.py in the background to fetch and process new videos.
    Returns immediately while processing continues in background.
    """
    global processing_status
    
    if processing_status["is_processing"]:
        return JSONResponse(
            status_code=409,
            content={
                "status": "already_processing",
                "message": "Video processing already in progress",
                "started_at": processing_status["last_run"]
            }
        )
    
    # Add background task
    background_tasks.add_task(run_youtube_monitor)
    
    return {
        "status": "started",
        "message": "Video processing started in background",
        "started_at": datetime.now().isoformat(),
        "note": "Check /status endpoint for progress"
    }


@app.get("/status")
async def status():
    """
    Get status of video processing pipeline.
    
    Shows whether processing is currently running and results of last run.
    """
    return {
        "is_processing": processing_status["is_processing"],
        "last_run": processing_status["last_run"],
        "last_result": processing_status["last_result"]
    }


@app.get("/stats")
async def stats():
    """
    Get database statistics.
    
    Returns total videos, breakdown by channel, source types, and date range.
    """
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="Database not found. Run /ingest first.")
    
    try:
        db_stats = get_stats()
        
        return {
            "total_videos": db_stats['total_videos'],
            "date_range": db_stats['date_range'],
            "by_channel": db_stats['by_channel'],
            "by_source": db_stats['by_source']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")


@app.get("/videos/{video_id}")
async def get_video(video_id: str):
    """
    Get a specific video by YouTube video ID.
    
    Example: /videos/xsoAkbIhM4w
    """
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="Database not found. Run /ingest first.")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
        
        video = dict(row)
        
        return {
            "video_id": video['video_id'],
            "title": video['video_title'],
            "channel": video['channel_name'],
            "url": video['video_url'],
            "published": video['published_date'],
            "processed": video['processed_date'],
            "duration": video.get('duration_seconds', 0),
            "source_type": video['source_type'],
            "summary": video['summary_text'],
            "key_topics": video.get('key_topics'),
            "recommendations": video.get('recommendations'),
            "action_items": video.get('action_items')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")


@app.get("/channels")
async def list_channels():
    """
    List all channels in the database with video counts.
    """
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="Database not found. Run /ingest first.")
    
    try:
        db_stats = get_stats()
        
        channels = [
            {
                "name": channel,
                "video_count": count
            }
            for channel, count in db_stats['by_channel'].items()
        ]
        
        # Sort by video count descending
        channels.sort(key=lambda x: x['video_count'], reverse=True)
        
        return {
            "total_channels": len(channels),
            "channels": channels
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Channel listing failed: {str(e)}")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database_exists": DB_PATH.exists(),
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting YouTube Research Assistant API...")
    print("📊 API Documentation: http://localhost:8001/docs")
    print("🔍 Interactive API: http://localhost:8001/redoc")
    print()
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )

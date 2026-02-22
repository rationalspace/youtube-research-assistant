# YouTube Research Assistant API Documentation

## Overview

FastAPI server running on port 8001 that provides REST endpoints to query the research.db database and trigger video processing.

## Quick Start

### Installation

```bash
# Install dependencies (done automatically by start_server.sh)
pip install fastapi uvicorn
```

### Starting the Server

```bash
chmod +x start_server.sh
./start_server.sh
```

The server will start on `http://localhost:8001`

### Interactive Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## API Endpoints

### 1. GET `/ask` - Semantic Keyword Search

Search across video summaries with optional date filtering.

**Parameters:**
- `q` (required): Search query
- `days` (optional): Filter videos from last N days
- `limit` (optional): Maximum results (default: 10, max: 100)

**Examples:**

```bash
# Search for Tesla mentions
curl "http://localhost:8001/ask?q=TSLA"

# Search last 7 days
curl "http://localhost:8001/ask?q=artificial%20intelligence&days=7"

# Search with limit
curl "http://localhost:8001/ask?q=NVDA&limit=5"
```

**Response:**

```json
{
  "query": "TSLA",
  "days": null,
  "from_date": null,
  "count": 3,
  "results": [
    {
      "video_id": "xsoAkbIhM4w",
      "title": "Tesla Q4 Analysis",
      "channel": "@parkevtatevosiancfa9544",
      "url": "https://youtube.com/watch?v=xsoAkbIhM4w",
      "published": "2026-01-30T12:01:51Z",
      "duration": 1239,
      "source_type": "youtube_captions",
      "summary": "Full summary text...",
      "key_topics": null,
      "recommendations": null,
      "action_items": null
    }
  ]
}
```

---

### 2. GET `/digest` - Structured Recent Digest

Get a structured digest of recent videos grouped by channel.

**Parameters:**
- `days` (optional): Number of days to include (default: 7, max: 90)

**Examples:**

```bash
# Get last 7 days
curl "http://localhost:8001/digest?days=7"

# Get last 30 days
curl "http://localhost:8001/digest?days=30"
```

**Response:**

```json
{
  "period": {
    "days": 7,
    "from": "2026-02-15",
    "to": "2026-02-22"
  },
  "summary": {
    "total_videos": 21,
    "total_channels": 5,
    "channels": [
      {
        "name": "@parkevtatevosiancfa9544",
        "video_count": 9
      },
      {
        "name": "@AkshatZayn",
        "video_count": 6
      }
    ]
  },
  "videos_by_channel": {
    "@parkevtatevosiancfa9544": [
      {
        "video_id": "xsoAkbIhM4w",
        "title": "Tesla Analysis",
        "url": "https://youtube.com/watch?v=xsoAkbIhM4w",
        "published": "2026-01-30T12:01:51Z",
        "duration": 1239,
        "summary": "..."
      }
    ]
  }
}
```

---

### 3. POST `/ingest` - Trigger Video Processing

Triggers the youtube_monitor.py pipeline to check for new videos.

Runs `check_once.py` in the background and returns immediately.

**Example:**

```bash
curl -X POST "http://localhost:8001/ingest"
```

**Response:**

```json
{
  "status": "started",
  "message": "Video processing started in background",
  "started_at": "2026-02-22T10:30:00",
  "note": "Check /status endpoint for progress"
}
```

**If already processing:**

```json
{
  "status": "already_processing",
  "message": "Video processing already in progress",
  "started_at": "2026-02-22T10:25:00"
}
```

---

### 4. GET `/status` - Processing Status

Check the status of the video processing pipeline.

**Example:**

```bash
curl "http://localhost:8001/status"
```

**Response (Processing):**

```json
{
  "is_processing": true,
  "last_run": "2026-02-22T10:30:00",
  "last_result": null
}
```

**Response (Completed):**

```json
{
  "is_processing": false,
  "last_run": "2026-02-22T10:30:00",
  "last_result": {
    "success": true,
    "stdout": "...",
    "stderr": "",
    "return_code": 0
  }
}
```

---

### 5. GET `/stats` - Database Statistics

Get overall database statistics.

**Example:**

```bash
curl "http://localhost:8001/stats"
```

**Response:**

```json
{
  "total_videos": 127,
  "date_range": {
    "from": "2026-01-15T10:30:00Z",
    "to": "2026-02-22T08:00:00Z"
  },
  "by_channel": {
    "@parkevtatevosiancfa9544": 45,
    "@AkshatZayn": 38,
    "@FinTek": 28,
    "@SahilBhadviya": 10,
    "@TickerSymbolYOU": 6
  },
  "by_source": {
    "youtube_captions": 105,
    "audio_transcription": 22
  }
}
```

---

### 6. GET `/videos/{video_id}` - Get Specific Video

Retrieve a specific video by YouTube video ID.

**Example:**

```bash
curl "http://localhost:8001/videos/xsoAkbIhM4w"
```

**Response:**

```json
{
  "video_id": "xsoAkbIhM4w",
  "title": "Tesla Q4 Analysis",
  "channel": "@parkevtatevosiancfa9544",
  "url": "https://youtube.com/watch?v=xsoAkbIhM4w",
  "published": "2026-01-30T12:01:51Z",
  "processed": "2026-01-31T08:00:00",
  "duration": 1239,
  "source_type": "youtube_captions",
  "summary": "Full summary...",
  "key_topics": null,
  "recommendations": null,
  "action_items": null
}
```

---

### 7. GET `/channels` - List Channels

List all channels with video counts.

**Example:**

```bash
curl "http://localhost:8001/channels"
```

**Response:**

```json
{
  "total_channels": 5,
  "channels": [
    {
      "name": "@parkevtatevosiancfa9544",
      "video_count": 45
    },
    {
      "name": "@AkshatZayn",
      "video_count": 38
    }
  ]
}
```

---

### 8. GET `/health` - Health Check

Simple health check endpoint.

**Example:**

```bash
curl "http://localhost:8001/health"
```

**Response:**

```json
{
  "status": "healthy",
  "database_exists": true,
  "timestamp": "2026-02-22T10:30:00"
}
```

---

## Usage Examples

### Python

```python
import requests

# Search for videos
response = requests.get("http://localhost:8001/ask", params={
    "q": "TSLA",
    "days": 7,
    "limit": 5
})
results = response.json()

for video in results['results']:
    print(f"{video['title']}: {video['summary'][:100]}...")

# Get digest
digest = requests.get("http://localhost:8001/digest", params={"days": 7}).json()
print(f"Total videos: {digest['summary']['total_videos']}")

# Trigger processing
response = requests.post("http://localhost:8001/ingest")
print(response.json())
```

### JavaScript

```javascript
// Search for videos
fetch('http://localhost:8001/ask?q=NVDA&days=7')
  .then(res => res.json())
  .then(data => {
    console.log(`Found ${data.count} videos`);
    data.results.forEach(video => {
      console.log(`${video.title}: ${video.url}`);
    });
  });

// Trigger processing
fetch('http://localhost:8001/ingest', { method: 'POST' })
  .then(res => res.json())
  .then(data => console.log(data.message));
```

### cURL

```bash
# Search
curl "http://localhost:8001/ask?q=stock%20market&days=7&limit=10"

# Get digest
curl "http://localhost:8001/digest?days=30"

# Trigger processing
curl -X POST "http://localhost:8001/ingest"

# Check status
curl "http://localhost:8001/status"

# Get stats
curl "http://localhost:8001/stats"

# Get specific video
curl "http://localhost:8001/videos/xsoAkbIhM4w"
```

---

## Automation Examples

### Scheduled Ingestion

```bash
# Add to crontab to ingest daily at 8 AM
0 8 * * * curl -X POST http://localhost:8001/ingest
```

### Morning Digest Email

```python
import requests
import smtplib
from email.mime.text import MIMEText

# Get digest
digest = requests.get("http://localhost:8001/digest?days=1").json()

# Format email
email_body = f"Daily Video Digest\n\n"
email_body += f"Total videos: {digest['summary']['total_videos']}\n\n"

for channel, videos in digest['videos_by_channel'].items():
    email_body += f"\n{channel}:\n"
    for video in videos:
        email_body += f"  - {video['title']}\n"
        email_body += f"    {video['summary'][:200]}...\n\n"

# Send email
# ... (your SMTP code here)
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200` - Success
- `404` - Resource not found
- `409` - Conflict (e.g., already processing)
- `500` - Server error
- `503` - Service unavailable (e.g., database not found)

**Error Response Format:**

```json
{
  "detail": "Error message here"
}
```

---

## Performance

- **Search queries**: < 100ms (with FTS index)
- **Digest generation**: < 500ms for 100 videos
- **Ingest trigger**: Returns immediately (< 10ms)
- **Stats**: < 50ms

---

## Security Considerations

⚠️ **Current Implementation:**
- No authentication/authorization
- Runs on localhost only (0.0.0.0:8001)
- CORS enabled for all origins

**For Production:**

1. Add API key authentication
2. Restrict CORS origins
3. Add rate limiting
4. Use HTTPS
5. Add request validation
6. Implement proper logging

---

## Development

### Running in Dev Mode

```bash
./start_server.sh
```

Server auto-reloads on code changes.

### Testing

```bash
# Test search
curl "http://localhost:8001/ask?q=test"

# Test digest
curl "http://localhost:8001/digest?days=7"

# Test health
curl "http://localhost:8001/health"
```

### Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.

---

## Troubleshooting

**Server won't start:**
- Check port 8001 isn't already in use: `lsof -i :8001`
- Ensure FastAPI is installed: `pip install fastapi uvicorn`
- Check virtual environment is activated

**Database not found error:**
- Run `./run-once.sh` first to create the database
- Check `research.db` exists in the project directory

**Ingest doesn't work:**
- Ensure `check_once.py` exists and is executable
- Check `.env` file has all required API keys
- View logs in `/status` endpoint for errors

**Search returns no results:**
- Check database has data: `curl localhost:8001/stats`
- Try broader search terms
- Check date range isn't excluding all videos

---

## Future Enhancements

Potential improvements:
- WebSocket support for real-time updates
- GraphQL endpoint
- Batch processing endpoints
- Export endpoints (CSV, JSON, PDF)
- Analytics dashboard
- User management
- Saved searches
- Email subscriptions
- Webhook notifications

---

## API Client Libraries

### Python Client Example

```python
class YouTubeResearchClient:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
    
    def search(self, query, days=None, limit=10):
        params = {"q": query, "limit": limit}
        if days:
            params["days"] = days
        return requests.get(f"{self.base_url}/ask", params=params).json()
    
    def digest(self, days=7):
        return requests.get(f"{self.base_url}/digest", params={"days": days}).json()
    
    def ingest(self):
        return requests.post(f"{self.base_url}/ingest").json()
    
    def status(self):
        return requests.get(f"{self.base_url}/status").json()

# Usage
client = YouTubeResearchClient()
results = client.search("TSLA", days=7)
```

---

**Built with FastAPI** 🚀

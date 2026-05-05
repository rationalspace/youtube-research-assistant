# YouTube Research Assistant 🤖📺

Automated YouTube video summarization tool that monitors your favourite creators, generates deep AI-powered insights, stores everything in a local database, and delivers profile-specific email digests — all for $0/month.

## 🎯 What It Does

- **Monitors** multiple YouTube channels across configurable profiles
- **Extracts** video transcripts (falls back to audio transcription if captions unavailable)
- **Summarizes** content using Gemini 2.5 Flash with profile-specific prompts
- **Stores** every summary in a local SQLite database with full-text search
- **Delivers** separate email digests per profile (Finance + PM/AI)
- **Exposes** a REST API for querying and integrating summaries downstream
- **Costs** $0/month to run (uses free APIs)

## ✨ Features

- ✅ **Smart Transcript Extraction** — Tries YouTube captions, auto-generated, then audio fallback
- ✅ **Audio Fallback** — Downloads and transcribes audio via Gemini when captions aren't available
- ✅ **SQLite Local Storage** — Every summary persisted in `research.db` with FTS5 full-text search
- ✅ **REST API** — FastAPI server on port 8001 to query summaries and trigger ingestion
- ✅ **Multi-Profile Monitoring** — Finance (5 channels) + PM/AI (3 channels) with custom prompts
- ✅ **Per-Profile Email Digests** — Each profile sends its own email with a `[profile]` subject prefix
- ✅ **Duplicate Detection** — Tracks processed videos per profile to avoid redundant work
- ✅ **Member-Only Detection** — Automatically skips restricted content
- ✅ **Quota-Aware Early Exit** — Distinguishes fatal daily-limit exhaustion from recoverable per-minute rate limits; retries per-minute limits with a 65s backoff and exits immediately on daily exhaustion — no wasted retries, no bad emails
- ✅ **Daily Automation** — Set it and forget it with cron

## 🏗️ Architecture

```
YouTube Channels
      │
      ▼
┌─────────────────────────────────────────┐
│  Monitor Layer  (youtube_monitor.py)    │
│  - Per-profile YAML config              │
│  - Transcript extraction + AI summary   │
│  - check_once.py --profile <name>       │
└────────────────┬────────────────────────┘
                 │ stores every summary
                 ▼
┌─────────────────────────────────────────┐
│  Database Layer  (db_manager.py)        │
│  - SQLite: research.db                  │
│  - FTS5 full-text search index          │
│  - query_db.py CLI tool                 │
└────────────────┬────────────────────────┘
                 │ queried by
                 ▼
┌─────────────────────────────────────────┐
│  API Layer  (api.py — port 8001)        │
│  - GET  /ask?q=TSLA&days=7              │
│  - GET  /digest?days=7                  │
│  - POST /ingest                         │
│  - GET  /stats  /channels  /health      │
└─────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- macOS, Linux, or Windows
- Python 3.8+
- FFmpeg: `brew install ffmpeg`
- API Keys: YouTube Data API v3, Google Gemini API, Gmail App Password

### Installation

```bash
git clone https://github.com/yourusername/youtube-research-assistant.git
cd youtube-research-assistant
chmod +x setup.sh && ./setup.sh
cp .env.template .env
nano .env   # fill in your API keys
```

### Run both profiles (sends 2 emails)

```bash
./run-once.sh
```

### (Optional) Start the API server

```bash
./start_server.sh
# → http://localhost:8001/docs
```

## 🔑 Getting API Keys

| Key | Where |
|-----|-------|
| YouTube Data API v3 | [Google Cloud Console](https://console.cloud.google.com/) → Enable "YouTube Data API v3" → Create credentials |
| Gemini API Key | [Google AI Studio](https://aistudio.google.com/app/apikey) → Create API key (FREE) |
| Gmail App Password | Google Account → Security → 2-Step Verification → App passwords → Mail |

## 👤 Profiles

Each profile is a YAML file in `profiles/` that defines channels and an AI prompt.

### Built-in profiles

| Profile | Channels | Focus |
|---------|----------|-------|
| `finance` | Parkev, AkshatZayn, FinTek, SahilBhadviya, TickerSymbolYOU | Tickers, price targets, buy/sell ratings |
| `pm_ai` | TheSkipPodcast, PeterYangYT, MaheshAIPMCommunity | Frameworks, AI tools, career advice, deep `[REF]`/`[TOOL]` analysis |

### Run a specific profile manually

```bash
source venv/bin/activate
python check_once.py --profile finance
python check_once.py --profile pm_ai
```

### Add a new profile

Create `profiles/myprofile.yaml`:

```yaml
channels:
  - url: "https://www.youtube.com/@SomeChannel"
    handle: "@SomeChannel"

enable_reading_queue: false

prompt: |
  Analyze this video and provide a summary.

  Video Title: {title}
  Channel: {channel}
  Published: {published}

  Transcript:
  {transcript}
```

Then run:
```bash
python check_once.py --profile myprofile
```

## 🗄️ Database

Every processed video is automatically saved to `research.db` (SQLite) during each run. No setup required — the database is created on first run.

### Query via CLI

```bash
# Search for a keyword
python query_db.py search "TSLA"

# Search with date filter
python query_db.py search "AI product" --days 30

# Get a specific video
python query_db.py get <video_id>

# Database stats
python query_db.py stats
```

### Query via API

```bash
# Full-text search
curl "http://localhost:8001/ask?q=TSLA&days=7"

# Weekly digest
curl "http://localhost:8001/digest?days=7"

# Stats
curl "http://localhost:8001/stats"
```

See `DATABASE_FEATURE.md` for schema details and advanced queries.

## 🔌 API Server

Start the server:
```bash
./start_server.sh   # runs on http://localhost:8001
```

| Endpoint | Description |
|----------|-------------|
| `GET /ask?q=<query>&days=<n>` | Full-text search across all summaries |
| `GET /digest?days=<n>` | Recent videos grouped by channel |
| `POST /ingest` | Trigger video processing in background |
| `GET /status` | Check if processing is running |
| `GET /stats` | DB stats (total, by channel, by source) |
| `GET /channels` | List all channels with video counts |
| `GET /videos/{video_id}` | Get a specific video by YouTube ID |
| `GET /health` | Health check |

Interactive docs: [http://localhost:8001/docs](http://localhost:8001/docs)

See `API_DOCUMENTATION.md` for full details and code examples.

## ⏰ Cron / Daily Automation

Each profile has its own cron-friendly shell script. Finance runs every day; PM/AI runs Mon/Wed/Fri to avoid burning through the Gemini free quota on less-active channels.

### macOS/Linux cron setup

```bash
crontab -e
```

```cron
# Finance: every day at 8 AM
0 8 * * * cd /path/to/youtube-research-assistant && PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin /bin/bash run-finance.sh >> cron.log 2>&1

# PM/AI: Monday, Wednesday, Friday at 8 AM
0 8 * * 1,3,5 cd /path/to/youtube-research-assistant && PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin /bin/bash run-pm-ai.sh >> cron.log 2>&1
```

> **Quota handling:** If the YouTube or Gemini API quota is exhausted mid-run, the script stops immediately, skips sending the email for that run, logs `🚫 API quota exhausted`, and exits cleanly. The next scheduled cron run picks up where it left off.

## 📁 Project Structure

```
youtube-research-assistant/
├── youtube_monitor.py        # Core monitor: transcript extraction + AI summarization
├── check_once.py             # Single-run entry point (requires --profile)
├── db_manager.py             # SQLite schema, CRUD, FTS5 full-text search
├── api.py                    # FastAPI server (port 8001)
├── query_db.py               # CLI tool for querying research.db
├── profiles/
│   ├── finance.yaml          # Finance profile: 5 channels, ticker/rating prompt
│   └── pm_ai.yaml            # PM/AI profile: 3 channels, deep analysis + GO DEEPER prompt
├── research.db               # SQLite database (auto-created on first run)
├── run-finance.sh            # Cron script: runs finance profile → sends email
├── run-pm-ai.sh              # Cron script: runs pm_ai profile → sends email
├── run-once.sh               # Generic single-run wrapper (pass --profile <name>)
├── run.sh                    # Continuous mode (checks every 24h, pass --profile <name>)
├── start_server.sh           # Starts FastAPI server on port 8001
├── setup.sh                  # One-time setup
├── requirements.txt          # Python dependencies
├── .env.template             # Environment variables template
├── summaries/                # File output per profile (summaries/finance/, summaries/pm_ai/)
├── API_DOCUMENTATION.md      # Full API reference
├── DATABASE_FEATURE.md       # Database schema and query guide
└── SETUP_GUIDE.md            # Detailed setup instructions
```

## 🛠️ Tech Stack

- **Python 3.8+**
- **YouTube Data API v3** — Video metadata and channel info
- **yt-dlp** — Audio extraction fallback
- **Google Gemini 2.0 Flash** — AI transcription and summarization (1,500 req/day free)
- **SQLite + FTS5** — Local storage with full-text search
- **FastAPI** — REST API layer
- **PyYAML** — Profile configuration
- **Gmail SMTP** — Email delivery
- **FFmpeg** — Audio processing

## 💰 Cost

**$0/month** using:
- YouTube Data API (free tier: 10,000 units/day)
- Google Gemini Flash (free)
- Gmail (free)

## 🐛 Troubleshooting

**Summaries showing "Unable to generate"?**
- Usually means `youtube-transcript-api` version mismatch. Ensure v1.x compatible code is in place.
- Check console for `Error downloading audio` — verify FFmpeg is installed: `ffmpeg -version`

**No emails received?**
- Check Gmail App Password (16 characters, no spaces) and that 2FA is enabled
- Check spam folder

**`ModuleNotFoundError: No module named 'yaml'`?**
```bash
source venv/bin/activate && pip install PyYAML
```

**`🚫 API quota exhausted` in cron.log?**
- This is expected when the YouTube Data API (10,000 units/day free) or Gemini free quota is hit
- The script exits cleanly — no email is sent, no videos are double-processed
- Quota resets at midnight Pacific — the next scheduled cron run will proceed normally
- To reduce quota usage: lower `videos_per_channel` in your profile YAML, or reduce cron frequency

**Gemini keeps retrying even after daily quota is hit?**
- Ensure you are on the latest code (`git pull origin main`)
- Old versions misclassified the combined per-day + per-minute violation as a recoverable per-minute limit, causing 4×65s retries per video before giving up
- The fix in `_is_rate_limit_error()` treats any error that contains a per-day violation as fatal, so the script exits immediately instead of retrying

**API /ingest not working?**
- Known issue: `/ingest` endpoint currently requires a `--profile` fix — use `./run-finance.sh` or `./run-pm-ai.sh` for now

## 🤝 Contributing

Ideas welcome:
- Slack/Discord integration
- Web dashboard for summaries
- More profile templates (Health, Tech News, etc.)
- Better member-only detection

## 📝 License

MIT License

## 📧 Contact

Built by [Mandeep Makkar](https://www.linkedin.com/in/mandeep-makkar/) — AI Product Leader with 18+ years in product management.

---

**⭐ If this saves you time, give it a star!**

# YouTube Research Assistant 🤖📺

Automated YouTube video summarization tool that delivers AI-generated insights directly to your inbox. Monitor your favorite creators, get daily summaries with key takeaways, and never fall behind on content again.

## 🎯 What It Does

- **Monitors** multiple YouTube channels of your choice
- **Extracts** video transcripts (or transcribes audio if captions unavailable)
- **Summarizes** content using AI with key topics, recommendations, and action items
- **Delivers** daily email digests with all summaries
- **Saves** backup copies locally
- **Costs** $0/month to run (uses free APIs)

Perfect for:
- 📈 Investment research enthusiasts
- 🏃 Health & wellness followers
- 💻 Tech news junkies
- 📚 Educational content consumers
- 🎯 Anyone drowning in YouTube videos they want to watch but don't have time for

## ✨ Features

- ✅ **Smart Transcript Extraction** - Tries multiple methods (captions, auto-generated, audio transcription)
- ✅ **Audio Fallback** - Downloads and transcribes audio when captions aren't available
- ✅ **Duplicate Detection** - Tracks processed videos to avoid redundant work
- ✅ **Email + File Output** - Get summaries via email AND saved locally
- ✅ **Shorts Included** - Processes all video lengths including YouTube Shorts
- ✅ **Member-Only Detection** - Automatically skips restricted content
- ✅ **Customizable Summaries** - Define exactly what insights you need
- ✅ **Daily Automation** - Set it and forget it with cron/LaunchAgent

## 🚀 Quick Start

### Prerequisites

- macOS, Linux, or Windows
- Python 3.8+
- FFmpeg (for audio extraction)
- API Keys:
  - YouTube Data API v3 (free)
  - Google Gemini API (free with Gemini Pro)
  - Gmail account with App Password

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/youtube-research-assistant.git
cd youtube-research-assistant
```

2. **Run setup:**
```bash
chmod +x setup.sh
./setup.sh
```

3. **Install FFmpeg:**
```bash
# macOS
brew install ffmpeg

# Linux (Ubuntu/Debian)
sudo apt install ffmpeg

# Windows
winget install ffmpeg
```

4. **Configure API keys:**
```bash
cp .env.template .env
nano .env  # Add your API keys
```

5. **Test it:**
```bash
./run-once.sh
```

## 🔑 Getting API Keys

### YouTube API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "YouTube Data API v3"
4. Create credentials → API Key
5. Copy the key

### Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API key"
4. Copy the key (FREE with Gemini Pro!)

### Gmail App Password
1. Go to your [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Scroll to "App passwords"
4. Generate password for "Mail"
5. Copy the 16-character password

## ⚙️ Configuration

Edit `youtube_monitor.py` to customize:

```python
CONFIG = {
    "channels": [
        {
            "url": "https://www.youtube.com/@YourChannel1",
            "handle": "@YourChannel1"
        },
        {
            "url": "https://www.youtube.com/@YourChannel2",
            "handle": "@YourChannel2"
        },
    ],
    "videos_per_channel": 3,  # How many latest videos to check
    "check_interval_hours": 24,  # For continuous mode
    "output_directory": "summaries",
}
```

Customize the summary prompt in `SUMMARY_PROMPT` to get the insights you need.

## 📅 Daily Automation

### macOS/Linux (cron)
```bash
crontab -e

# Add this line (runs at 8 AM daily):
0 8 * * * cd /path/to/youtube-research-assistant && ./run-once.sh
```

### macOS (LaunchAgent)
See `DAILY_AUTOMATION_SETUP.md` for detailed instructions.

## 📖 Usage

### Run Once
```bash
./run-once.sh
```

### Force Reprocess All Videos
```bash
python check_once.py --force
```

### Run Continuously (checks every 24 hours)
```bash
./run.sh
```

### Test Specific Channels
```bash
python test_channels.py
```

## 📁 Project Structure

```
youtube-research-assistant/
├── youtube_monitor.py          # Main script
├── check_once.py              # Single run script
├── setup.sh                   # Automated setup
├── run.sh                     # Continuous mode runner
├── run-once.sh               # Single check runner
├── requirements.txt          # Python dependencies
├── .env.template             # Environment variables template
├── summaries/                # Output directory for summaries
└── README.md
```

## 🛠️ Tech Stack

- **Python 3.8+**
- **YouTube Data API v3** - Video metadata and channel info
- **yt-dlp** - Audio extraction when needed
- **Google Gemini 2.5 Flash** - AI transcription and summarization
- **Gmail SMTP** - Email delivery
- **FFmpeg** - Audio processing

## 💰 Cost

**$0/month** if you use:
- YouTube Data API (free tier: 10,000 units/day)
- Google Gemini Flash (FREE with Gemini Pro subscription)
- Gmail (free)

## 🐛 Troubleshooting

**No transcripts available?**
- Wait 30-60 min for new videos (auto-captions take time)
- The script will automatically try audio transcription as fallback

**Email not sending?**
- Check Gmail App Password (16 characters, no spaces)
- Verify 2FA is enabled on Google account
- Check spam folder

**Audio transcription failing?**
- Ensure FFmpeg is installed: `ffmpeg -version`
- Check Gemini API quota
- Video might be members-only or restricted

See `TROUBLESHOOTING_TRANSCRIPTS.md` for more help.

## 🤝 Contributing

Contributions welcome! This started as a weekend project to solve a personal problem, but it could help many others.

**Ideas for contributions:**
- Support for more video platforms (Vimeo, etc.)
- Slack/Discord integration instead of email
- Web dashboard for viewing summaries
- Support for playlists
- Multi-language support
- Better member-only detection

## 📝 License

MIT License - feel free to use this for personal or commercial projects!

## 🙏 Acknowledgments

Built with:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for robust YouTube downloading
- [Google Gemini](https://ai.google.dev/) for AI transcription and summarization
- [Claude](https://www.anthropic.com/claude) for development assistance

## 📧 Contact

Built by [Mandeep Makkar](https://www.linkedin.com/in/mandeep-makkar/) - AI Product Leader with 18+ years in product management.

Currently seeking AI Product Leadership opportunities. Let's connect!

---

**⭐ If this saves you time, give it a star!**

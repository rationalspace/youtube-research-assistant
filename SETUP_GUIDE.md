# YouTube Financial Video Monitor - Setup Guide

## Overview
This automated system monitors YouTube channels for new financial content, generates AI-powered summaries using Claude, and emails you daily reports.

## What You'll Need

### 1. YouTube Data API Key
- Go to: https://console.cloud.google.com/
- Create a new project or select existing one
- Enable "YouTube Data API v3"
- Create credentials (API Key)
- Copy the API key

### 2. Gemini API Key
- Go to: https://aistudio.google.com/app/apikey
- Sign in with your Google account (the one with Gemini Pro)
- Click "Create API key"
- Copy the key
- **Note**: With Gemini Pro, you get FREE access to Gemini Flash!

### 3. Gmail App Password
Since Gmail requires 2FA for app access:
- Go to your Google Account settings
- Navigate to Security > 2-Step Verification
- Scroll down to "App passwords"
- Generate a new app password for "Mail"
- Copy the 16-character password (no spaces)

## Installation Steps

### Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set Environment Variables

#### On Mac/Linux:
Create a `.env` file or add to your `.bashrc`/`.zshrc`:
```bash
export YOUTUBE_API_KEY="your_youtube_api_key_here"
export GEMINI_API_KEY="your_gemini_api_key_here"
export GMAIL_USER="your.email@gmail.com"
export GMAIL_APP_PASSWORD="your_16_char_app_password"
export RECIPIENT_EMAIL="recipient@email.com"  # Optional, defaults to GMAIL_USER
```

Then run:
```bash
source .env
```

#### On Windows (PowerShell):
```powershell
$env:YOUTUBE_API_KEY="your_youtube_api_key_here"
$env:GEMINI_API_KEY="your_gemini_api_key_here"
$env:GMAIL_USER="your.email@gmail.com"
$env:GMAIL_APP_PASSWORD="your_16_char_app_password"
$env:RECIPIENT_EMAIL="recipient@email.com"
```

#### Using a .env file (recommended):
Create a file named `.env` in the same directory:
```
YOUTUBE_API_KEY=your_youtube_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
RECIPIENT_EMAIL=recipient@email.com
```

Then modify the script to load it (add at the top):
```python
from dotenv import load_dotenv
load_dotenv()
```

## Usage

### Run Once (Manual Check)
```bash
python youtube_monitor.py
```
This will check once and exit.

### Run Continuously (Daily Automated Checks)
The script runs continuously by default, checking every 24 hours:
```bash
python youtube_monitor.py
```

To stop: Press `Ctrl+C`

### Run as Background Service

#### On Mac/Linux:
```bash
# Run in background
nohup python youtube_monitor.py > youtube_monitor.log 2>&1 &

# Check if running
ps aux | grep youtube_monitor

# View logs
tail -f youtube_monitor.log

# Stop
pkill -f youtube_monitor.py
```

#### Using systemd (Linux):
Create `/etc/systemd/system/youtube-monitor.service`:
```ini
[Unit]
Description=YouTube Financial Video Monitor
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/script/directory
Environment="YOUTUBE_API_KEY=your_key"
Environment="GEMINI_API_KEY=your_key"
Environment="GMAIL_USER=your@email.com"
Environment="GMAIL_APP_PASSWORD=your_password"
ExecStart=/usr/bin/python3 /path/to/youtube_monitor.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable youtube-monitor
sudo systemctl start youtube-monitor
sudo systemctl status youtube-monitor
```

## Configuration

Edit the `CONFIG` dictionary in `youtube_monitor.py`:

```python
CONFIG = {
    "channels": [
        {
            "url": "https://www.youtube.com/@parkevtatevosiancfa9544",
            "handle": "@parkevtatevosiancfa9544"
        },
        # Add more channels here
    ],
    "check_interval_hours": 24,  # How often to check
    "lookback_hours": 25,  # How far back to look for videos
}
```

## Email Report Format

Each email will contain:
- Subject: "📊 Daily Financial Video Summary - X New Video(s)"
- For each video:
  - Title, Channel, Published date, URL
  - **Specific Tickers** mentioned
  - **Price Info** (targets, current prices, entry points)
  - **Rating** (Buy/Sell/Hold or sentiment)
  - **Investment Thesis** (the 'why')
  - **Actionability** (what to do next)

## Troubleshooting

### No emails received?
- Check Gmail spam folder
- Verify GMAIL_APP_PASSWORD is correct (16 characters, no spaces)
- Ensure 2FA is enabled on your Google account
- Check the console output for errors

### "Transcript not available" errors?
- Not all videos have transcripts (especially live streams)
- The script will note this in the summary

### API quota exceeded?
- YouTube API has daily quotas (usually 10,000 units/day)
- Each channel check uses ~3 units
- Reduce check frequency if needed

### Videos not being detected?
- Check that channel handles are correct
- Verify YOUTUBE_API_KEY is valid
- Videos must be public and have been published recently

## Cost Estimates

### YouTube Data API
- Free tier: 10,000 units/day
- This script uses ~50 units/day (very safe)

### Google Gemini Flash
- **FREE with Gemini Pro subscription!** 🎉
- No additional cost if you already have Gemini Pro
- Generous rate limits for personal use

### Gmail
- Free

**Total: $0/month** (assuming you already have Gemini Pro)

## Security Notes

⚠️ **Important Security Practices:**
- Never commit API keys to git
- Use environment variables or `.env` files
- Add `.env` to `.gitignore`
- Rotate API keys periodically
- Use app-specific passwords for Gmail (never your main password)

## Advanced Usage

### Schedule Specific Times (Using cron instead)
Instead of running continuously, use cron for specific times:

```bash
# Edit crontab
crontab -e

# Add this line to run at 8 AM daily
0 8 * * * /usr/bin/python3 /path/to/youtube_monitor.py --once
```

You'll need to modify the script to support `--once` flag.

### Multiple Recipients
Modify the `send_email` function to accept a list of recipients:
```python
msg['To'] = ', '.join(['email1@example.com', 'email2@example.com'])
```

### Customize Summary Prompt
Edit the `SUMMARY_PROMPT` variable to change how summaries are generated.

## Support

For issues:
1. Check the console output / log file
2. Verify all environment variables are set
3. Test API keys individually
4. Check YouTube channel URLs are correct

## Example Output

```
========================================================
YouTube Monitor Check - 2026-01-27 08:00:00
========================================================

Checking channel: @parkevtatevosiancfa9544
  Found 1 recent video(s)
  🆕 New video: Tesla Stock Analysis Q4 2025
  📝 Generating summary...
  ✓ Summary generated

✓ Email sent successfully to your@email.com

========================================================
Check complete!
========================================================

💤 Next check scheduled for: 2026-01-28 08:00:00
   Sleeping for 24 hours...
```

## License

MIT License - Use freely, modify as needed.

# Quick Start Guide for Mac

## 🚀 Super Simple Setup (3 Commands)

### 1. Make scripts executable and run setup
```bash
chmod +x setup.sh run.sh run-once.sh
./setup.sh
```

This will:
- Create a virtual environment (to avoid the pip error)
- Install all dependencies automatically
- Set everything up for you

### 2. Configure your API keys
```bash
cp .env.template .env
nano .env  # or use: open -e .env
```

Fill in these values in the `.env` file:

**YOUTUBE_API_KEY** - Get from:
1. Go to https://console.cloud.google.com/
2. Create/select a project
3. Enable "YouTube Data API v3"
4. Create credentials → API Key
5. Copy the key

**GEMINI_API_KEY** - Get from:
1. Go to https://aistudio.google.com/app/apikey
2. Sign in with your Google account (the one with Gemini Pro)
3. Click "Create API key"
4. Copy the key (it's FREE with Gemini Pro!)

**GMAIL_USER** - Your Gmail address (example@gmail.com)

**GMAIL_APP_PASSWORD** - Generate from:
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification (if not already)
3. Scroll to "App passwords"
4. Create new app password for "Mail"
5. Copy the 16-character password

**RECIPIENT_EMAIL** - Where to send reports (defaults to GMAIL_USER if blank)

### 3. Run it!
```bash
./run.sh
```

That's it! 🎉

## 🔧 Usage

### Run continuously (checks every 24 hours)
```bash
./run.sh
```

### Run once and exit (runs BOTH profiles → sends 2 emails)
```bash
./run-once.sh
```

### Run in background
```bash
nohup ./run.sh > monitor.log 2>&1 &
```

Check logs:
```bash
tail -f monitor.log
```

Stop it:
```bash
pkill -f youtube_monitor
```

## 🔍 Troubleshooting

### "Permission denied" error?
```bash
chmod +x setup.sh run.sh run-once.sh
```

### Need to reinstall?
```bash
rm -rf venv
./setup.sh
```

### Want to manually activate the virtual environment?
```bash
source venv/bin/activate
python youtube_monitor.py
```

To deactivate:
```bash
deactivate
```

## 📧 Testing Email

After setup, test with a single check:
```bash
./run-once.sh
```

This will immediately check all channels and send an email if new videos are found.

## ⏰ Schedule with Cron (Optional)

To run automatically at 8 AM every day:

```bash
# Edit crontab
crontab -e

# Add this line (replace /path/to with your actual path):
0 8 * * * cd /path/to/stock-summary-youtube && /bin/bash run-once.sh >> monitor.log 2>&1
```

## 📝 Add More Channels

Channels are configured in YAML profile files — **do not edit `youtube_monitor.py`**.

Edit the relevant profile in `profiles/`:

```yaml
# profiles/finance.yaml  (or profiles/pm_ai.yaml)
channels:
  - url: "https://www.youtube.com/@parkevtatevosiancfa9544"
    handle: "@parkevtatevosiancfa9544"
  # Add your new channel here:
  - url: "https://www.youtube.com/@YourNewChannel"
    handle: "@YourNewChannel"
```

To create a completely new profile, copy an existing YAML file and customise it:
```bash
cp profiles/finance.yaml profiles/myprofile.yaml
python check_once.py --profile myprofile
```

## 💰 Costs

- YouTube API: **FREE** (10,000 units/day quota)
- Gemini Flash: **FREE** (included with Gemini Pro)
- Gmail: **FREE**

**Total: $0/month!** 🎊

## ❓ Common Questions

**Q: How do I know it's working?**
A: Run `./run-once.sh` and you should see output like "Checking channel..." If there are new videos, you'll get an email.

**Q: Can I change how often it checks?**
A: Yes! Edit `youtube_monitor.py` and change `"check_interval_hours": 24` to whatever you want.

**Q: What if I don't get any emails?**
A: Check your spam folder, verify your Gmail app password is correct (16 characters, no spaces), and make sure 2FA is enabled on your Google account.

**Q: The script says "No new videos found"**
A: That's normal! It only emails when NEW videos are posted since the last check.

## 🔌 Start the API Server (Optional)

Query your summaries via REST API:

```bash
./start_server.sh
# → http://localhost:8001/docs
```

Key endpoints:
```bash
curl "http://localhost:8001/ask?q=TSLA&days=7"     # search summaries
curl "http://localhost:8001/digest?days=7"           # weekly digest by channel
curl "http://localhost:8001/stats"                   # database stats
```

## 🎯 Next Steps

Once everything is working:
1. Let it run for a day to test
2. Check your email — you'll get 2 emails (Finance + PM/AI)
3. (Optional) Start the API server to query summaries
4. Set up cron for automatic daily scheduling
5. Add more channels by editing the profile YAML files

For more details, see `SETUP_GUIDE.md`.

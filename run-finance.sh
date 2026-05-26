#!/bin/bash
# Run a single check for the finance profile and exit
# Scheduled via launchd: runs every day at 8 AM CST

# ---------------------------------------------------------------------------
# Stale-process guard — kill any leftover run from a previous invocation.
# check_once.py has a 30-min SIGALRM timeout, but that only fires if the
# Python interpreter stays responsive.  For total hangs (C-level block inside
# yt-dlp FFmpeg pipe or OS-level socket wait), the shell-side guard below is
# the last line of defence.
# ---------------------------------------------------------------------------
LOCKFILE="/tmp/youtube-monitor-finance.lock"

if [ -f "$LOCKFILE" ]; then
    OLD_PID=$(cat "$LOCKFILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "$(date): WARNING — previous finance run (PID $OLD_PID) is still alive. Killing stale process group..."
        # Kill the whole process group so yt-dlp / ffmpeg children die too.
        kill -TERM -- "-$OLD_PID" 2>/dev/null || kill -TERM "$OLD_PID" 2>/dev/null
        sleep 3
        kill -KILL -- "-$OLD_PID" 2>/dev/null || kill -KILL "$OLD_PID" 2>/dev/null || true
        echo "$(date): Stale process killed."
    fi
    rm -f "$LOCKFILE"
fi

# Write our PID so the next run can detect if we're still alive.
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

# Wait for network connectivity — launchd can fire before Wi-Fi is ready after sleep
echo "$(date): Waiting for network..."
for i in $(seq 1 12); do
    if curl -sf --max-time 5 https://www.googleapis.com > /dev/null 2>&1; then
        echo "$(date): Network ready."
        break
    fi
    echo "$(date): Network not ready, retrying in 10s (attempt $i/12)..."
    sleep 10
done

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first:"
    echo "   chmod +x setup.sh"
    echo "   ./setup.sh"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

echo "=========================================="
echo "🔍 Running check for profile: finance"
echo "=========================================="
echo ""
python check_once.py --profile finance
EXIT_CODE=$?
echo ""

exit $EXIT_CODE

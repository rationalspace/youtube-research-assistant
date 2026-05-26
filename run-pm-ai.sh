#!/bin/bash
# Run a single check for the pm_ai profile and exit
# Scheduled via launchd: runs Mon/Wed/Fri at 10 AM CST

# ---------------------------------------------------------------------------
# Stale-process guard — kill any leftover run from a previous invocation.
# ---------------------------------------------------------------------------
LOCKFILE="/tmp/youtube-monitor-pm-ai.lock"

if [ -f "$LOCKFILE" ]; then
    OLD_PID=$(cat "$LOCKFILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "$(date): WARNING — previous pm_ai run (PID $OLD_PID) is still alive. Killing stale process group..."
        kill -TERM -- "-$OLD_PID" 2>/dev/null || kill -TERM "$OLD_PID" 2>/dev/null
        sleep 3
        kill -KILL -- "-$OLD_PID" 2>/dev/null || kill -KILL "$OLD_PID" 2>/dev/null || true
        echo "$(date): Stale process killed."
    fi
    rm -f "$LOCKFILE"
fi

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
echo "🔍 Running check for profile: pm_ai"
echo "=========================================="
echo ""
python check_once.py --profile pm_ai
EXIT_CODE=$?
echo ""

exit $EXIT_CODE

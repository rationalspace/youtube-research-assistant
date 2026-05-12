#!/bin/bash
# Run a single check for the finance profile and exit
# Scheduled via launchd: runs every day at 8 AM CST

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

#!/bin/bash
# Run a single check for the finance profile and exit
# Used by cron: runs every day at 8 AM

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

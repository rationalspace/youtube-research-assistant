#!/bin/bash
# Run a single check for the pm_ai profile and exit
# Used by cron: runs Mon/Wed/Fri at 8 AM

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

#!/bin/bash
# Run a single check and exit

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first:"
    echo "   chmod +x setup.sh"
    echo "   ./setup.sh"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Run single check
echo "🔍 Running single check..."
echo ""
python check_once.py "$@"

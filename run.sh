#!/bin/bash
# Run script for YouTube Monitor

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first:"
    echo "   chmod +x setup.sh"
    echo "   ./setup.sh"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Run the monitor
echo "🚀 Starting YouTube Monitor..."
echo ""
python youtube_monitor.py

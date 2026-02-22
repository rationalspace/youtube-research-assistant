#!/bin/bash
# Start script for YouTube Research Assistant API

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first:"
    echo "   chmod +x setup.sh"
    echo "   ./setup.sh"
    exit 1
fi

# Set PATH to include Homebrew (for FFmpeg)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Activate virtual environment
source venv/bin/activate

# Check if FastAPI is installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing API dependencies..."
    pip install fastapi uvicorn --quiet
fi

# Start the server
echo "🚀 Starting YouTube Research Assistant API..."
echo ""
echo "API Endpoints:"
echo "  📖 Documentation:  http://localhost:8001/docs"
echo "  🔍 Search:         http://localhost:8001/ask?q=TSLA"
echo "  📊 Digest:         http://localhost:8001/digest?days=7"
echo "  ▶️  Trigger Ingest: POST http://localhost:8001/ingest"
echo "  📈 Stats:          http://localhost:8001/stats"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python api.py

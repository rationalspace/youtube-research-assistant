#!/bin/bash
# Setup script for YouTube Monitor on Mac/Linux

echo "🚀 YouTube Monitor Setup"
echo "======================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✓ pip upgraded"
echo ""

# Install requirements
echo "📥 Installing dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Copy .env.template to .env:"
    echo "   cp .env.template .env"
    echo ""
    echo "2. Edit .env and add your API keys:"
    echo "   nano .env"
    echo ""
    echo "3. Run the monitor:"
    echo "   ./run.sh"
    echo ""
    echo "Or activate the virtual environment manually:"
    echo "   source venv/bin/activate"
    echo "   python youtube_monitor.py"
else
    echo ""
    echo "❌ Installation failed. Please check the error messages above."
    exit 1
fi

#!/bin/bash
# Run a single check for all profiles and exit
# Sends one email per profile: finance + pm_ai

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first:"
    echo "   chmod +x setup.sh"
    echo "   ./setup.sh"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

PROFILES=("finance" "pm_ai")
EXIT_CODE=0

for profile in "${PROFILES[@]}"; do
    echo "=========================================="
    echo "🔍 Running check for profile: $profile"
    echo "=========================================="
    echo ""
    python check_once.py --profile "$profile"
    STATUS=$?
    if [ $STATUS -ne 0 ]; then
        echo "❌ Profile '$profile' exited with code $STATUS"
        EXIT_CODE=$STATUS
    fi
    echo ""
done

exit $EXIT_CODE

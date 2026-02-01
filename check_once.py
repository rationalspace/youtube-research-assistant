#!/usr/bin/env python3
"""
YouTube Monitor - Single Check Version
Run this once to check for new videos and send email.
Ideal for use with cron/Task Scheduler.
"""

import sys
import os

# Add support for .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Note: python-dotenv not installed. Using environment variables only.")

# Import the main monitor class
from youtube_monitor import YouTubeMonitor


def main():
    """Run a single check and exit."""
    try:
        print("🔍 Running single check...")
        monitor = YouTubeMonitor()
        monitor.check_channels()
        print("✅ Check complete!")
        return 0
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}\n")
        print("Setup instructions:")
        print("1. Copy .env.template to .env")
        print("2. Fill in your API keys and credentials")
        print("3. Run this script again")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

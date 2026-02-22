#!/usr/bin/env python3
"""
YouTube Monitor - Single Check Version
Run this once to check for new videos and send email.
Ideal for use with cron/Task Scheduler.
"""

import sys
import os
import argparse

# Add support for .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Note: python-dotenv not installed. Using environment variables only.")

# Import the main monitor class
from youtube_monitor import YouTubeMonitor, load_profile


def main():
    """Run a single check and exit."""
    parser = argparse.ArgumentParser(description='YouTube Monitor - Single Check')
    parser.add_argument(
        '--profile',
        required=True,
        metavar='PROFILE_NAME',
        help='Profile to use (e.g. finance, pm_ai)'
    )
    args = parser.parse_args()

    profile_config = load_profile(args.profile)

    try:
        print(f"🔍 Running single check for profile: {args.profile}")
        monitor = YouTubeMonitor(args.profile, profile_config)
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

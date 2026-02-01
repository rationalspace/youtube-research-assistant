#!/usr/bin/env python3
"""
Test script to verify the bug fix - checks if all 3 channels return videos
"""

import os
from dotenv import load_dotenv
load_dotenv()

from youtube_monitor import YouTubeMonitor

def test_channels():
    """Test that all 3 channels return videos."""
    print("🧪 Testing channel video retrieval...\n")
    
    try:
        monitor = YouTubeMonitor()
        
        channels = [
            ("@parkevtatevosiancfa9544", "Parkev Tatevosian"),
            ("@AkshatZayn", "Akshat Zayn"),
            ("@FinTek", "FinTek")
        ]
        
        for handle, name in channels:
            print(f"{'='*60}")
            print(f"Testing: {name} ({handle})")
            print(f"{'='*60}")
            
            channel_id = monitor.get_channel_id(handle)
            if not channel_id:
                print(f"❌ FAILED: Could not find channel ID\n")
                continue
            
            print(f"✓ Channel ID: {channel_id}")
            
            videos = monitor.get_latest_videos(channel_id, count=3)
            print(f"✓ Retrieved {len(videos)} videos\n")
            
            if len(videos) == 0:
                print(f"⚠️  WARNING: No videos found for this channel\n")
            else:
                for i, video in enumerate(videos, 1):
                    print(f"  Video {i}:")
                    print(f"    Title: {video['title']}")
                    print(f"    Duration: {video['duration_seconds']}s")
                    print(f"    Published: {video['published']}")
                    print(f"    ID: {video['id']}")
                    print()
        
        print(f"{'='*60}")
        print("✅ Test complete!")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_channels()

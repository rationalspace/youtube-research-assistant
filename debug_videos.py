#!/usr/bin/env python3
"""
Debug script to investigate why specific videos aren't being picked up
"""

import os
from dotenv import load_dotenv
load_dotenv()

from googleapiclient.discovery import build
import re

def parse_duration(duration_str):
    """Parse ISO 8601 duration format (e.g., 'PT15M33S') to seconds."""
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    
    if not match:
        return 0
    
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    
    return hours * 3600 + minutes * 60 + seconds

def debug_channel(handle):
    """Debug what videos are being returned for a channel."""
    youtube_api_key = os.getenv('YOUTUBE_API_KEY')
    youtube = build('youtube', 'v3', developerKey=youtube_api_key)
    
    print(f"\n{'='*80}")
    print(f"Debugging channel: {handle}")
    print(f"{'='*80}\n")
    
    # Get channel ID
    handle_clean = handle.replace('@', '')
    request = youtube.search().list(
        part='snippet',
        q=handle_clean,
        type='channel',
        maxResults=1
    )
    response = request.execute()
    
    if not response['items']:
        print(f"❌ Channel not found!")
        return
    
    channel_id = response['items'][0]['snippet']['channelId']
    print(f"✓ Channel ID: {channel_id}\n")
    
    # Get videos from channel (raw search results)
    print("Fetching last 15 videos from search API...")
    request = youtube.search().list(
        part='snippet',
        channelId=channel_id,
        type='video',
        order='date',
        maxResults=15
    )
    search_response = request.execute()
    
    video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
    print(f"✓ Found {len(video_ids)} videos in search results\n")
    
    if not video_ids:
        print("❌ No videos found!")
        return
    
    # Get detailed info for all videos
    print("Fetching detailed video information...\n")
    video_details_request = youtube.videos().list(
        part='contentDetails,status,snippet',
        id=','.join(video_ids)
    )
    video_details = video_details_request.execute()
    
    print(f"{'='*80}")
    print(f"VIDEO DETAILS (showing all {len(video_details['items'])} videos)")
    print(f"{'='*80}\n")
    
    for i, video in enumerate(video_details.get('items', []), 1):
        video_id = video['id']
        title = video['snippet']['title']
        published = video['snippet']['publishedAt']
        duration_str = video['contentDetails']['duration']
        duration_seconds = parse_duration(duration_str)
        privacy_status = video['status'].get('privacyStatus', 'unknown')
        description = video['snippet'].get('description', '')
        
        # Check member-only indicators
        title_lower = title.lower()
        description_lower = description.lower()
        member_indicators = ['members only', 'member exclusive', 'patreon', 'membership']
        is_member_only = any(indicator in title_lower or indicator in description_lower for indicator in member_indicators)
        
        print(f"Video {i}:")
        print(f"  Title: {title}")
        print(f"  Video ID: {video_id}")
        print(f"  URL: https://youtube.com/watch?v={video_id}")
        print(f"  Published: {published}")
        print(f"  Duration: {duration_seconds}s ({duration_str})")
        print(f"  Privacy: {privacy_status}")
        print(f"  Member-only detected: {is_member_only}")
        
        # Show filtering decision
        print(f"\n  FILTERING DECISION:")
        if duration_seconds < 60:
            print(f"    ❌ FILTERED OUT - Too short (< 60s)")
        elif privacy_status != 'public':
            print(f"    ❌ FILTERED OUT - Not public ({privacy_status})")
        elif is_member_only:
            print(f"    ❌ FILTERED OUT - Member-only content")
        else:
            print(f"    ✅ WOULD BE INCLUDED")
        
        print()

def debug_specific_video(video_id):
    """Debug a specific video by ID."""
    youtube_api_key = os.getenv('YOUTUBE_API_KEY')
    youtube = build('youtube', 'v3', developerKey=youtube_api_key)
    
    print(f"\n{'='*80}")
    print(f"Debugging specific video: {video_id}")
    print(f"{'='*80}\n")
    
    video_request = youtube.videos().list(
        part='contentDetails,status,snippet',
        id=video_id
    )
    response = video_request.execute()
    
    if not response['items']:
        print(f"❌ Video not found or not accessible!")
        return
    
    video = response['items'][0]
    title = video['snippet']['title']
    published = video['snippet']['publishedAt']
    duration_str = video['contentDetails']['duration']
    duration_seconds = parse_duration(duration_str)
    privacy_status = video['status'].get('privacyStatus', 'unknown')
    description = video['snippet'].get('description', '')
    channel_title = video['snippet']['channelTitle']
    
    # Check member-only indicators
    title_lower = title.lower()
    description_lower = description.lower()
    member_indicators = ['members only', 'member exclusive', 'patreon', 'membership']
    is_member_only = any(indicator in title_lower or indicator in description_lower for indicator in member_indicators)
    
    print(f"Title: {title}")
    print(f"Channel: {channel_title}")
    print(f"Published: {published}")
    print(f"Duration: {duration_seconds}s ({duration_str})")
    print(f"Privacy: {privacy_status}")
    print(f"Member-only detected: {is_member_only}")
    print(f"\nDescription (first 200 chars):")
    print(f"{description[:200]}...")
    
    print(f"\n{'='*80}")
    print(f"FILTERING DECISION:")
    if duration_seconds < 60:
        print(f"❌ FILTERED OUT - Too short (< 60s)")
    elif privacy_status != 'public':
        print(f"❌ FILTERED OUT - Not public ({privacy_status})")
    elif is_member_only:
        print(f"❌ FILTERED OUT - Member-only content detected")
    else:
        print(f"✅ SHOULD BE INCLUDED")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    # Debug the specific video mentioned
    print("\n🔍 DEBUGGING SPECIFIC VIDEO")
    debug_specific_video("xsoAkbIhM4w")
    
    # Debug all three channels
    print("\n\n🔍 DEBUGGING ALL CHANNELS")
    for handle in ["@parkevtatevosiancfa9544", "@AkshatZayn", "@FinTek"]:
        debug_channel(handle)
        input("\nPress Enter to continue to next channel...")


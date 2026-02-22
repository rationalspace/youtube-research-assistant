#!/usr/bin/env python3
"""
Query CLI for YouTube Research Database

Search and retrieve video summaries from the SQLite database.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from db_manager import search_videos, get_stats, get_video_by_id, DB_PATH

def format_video(video, show_full=False):
    """Format a video record for display."""
    output = []
    output.append("=" * 80)
    output.append(f"📺 {video['video_title']}")
    output.append("=" * 80)
    output.append(f"Channel: {video['channel_name']}")
    output.append(f"Published: {video['published_date']}")
    output.append(f"Duration: {video.get('duration_seconds', 0)}s")
    output.append(f"Source: {video['source_type']}")
    output.append(f"URL: {video['video_url']}")
    output.append("")
    
    if show_full:
        # Show full summary
        output.append("SUMMARY:")
        output.append("-" * 80)
        output.append(video['summary_text'])
        output.append("")
        
        if video.get('key_topics'):
            output.append("KEY TOPICS:")
            output.append(video['key_topics'])
            output.append("")
        
        if video.get('recommendations'):
            output.append("RECOMMENDATIONS:")
            output.append(video['recommendations'])
            output.append("")
        
        if video.get('action_items'):
            output.append("ACTION ITEMS:")
            output.append(video['action_items'])
            output.append("")
    else:
        # Show summary preview
        summary_preview = video['summary_text'][:300] + "..." if len(video['summary_text']) > 300 else video['summary_text']
        output.append("SUMMARY (preview):")
        output.append(summary_preview)
        output.append("")
        output.append("💡 Use --full to see complete summary")
        output.append("")
    
    return "\n".join(output)

def search_command(args):
    """Handle search command."""
    if not DB_PATH.exists():
        print("❌ Database not found. Run youtube_monitor.py first to create it.")
        return 1
    
    results = search_videos(
        search_term=args.query,
        from_date=args.from_date,
        channel=args.channel,
        limit=args.limit
    )
    
    if not results:
        print("📭 No videos found matching your criteria.")
        return 0
    
    print(f"\n🔍 Found {len(results)} video(s):\n")
    
    for i, video in enumerate(results, 1):
        print(format_video(video, show_full=args.full))
        if i < len(results):
            print("\n" + "─" * 80 + "\n")
    
    return 0

def stats_command(args):
    """Handle stats command."""
    if not DB_PATH.exists():
        print("❌ Database not found. Run youtube_monitor.py first to create it.")
        return 1
    
    stats = get_stats()
    
    print("\n📊 DATABASE STATISTICS")
    print("=" * 80)
    print(f"\nTotal videos: {stats['total_videos']}")
    
    if stats['date_range']['from']:
        print(f"Date range: {stats['date_range']['from']} to {stats['date_range']['to']}")
    
    print("\nVideos by channel:")
    for channel, count in stats['by_channel'].items():
        print(f"  • {channel}: {count}")
    
    print("\nVideos by source:")
    for source, count in stats['by_source'].items():
        print(f"  • {source}: {count}")
    
    print()
    return 0

def get_command(args):
    """Handle get command (get video by ID)."""
    if not DB_PATH.exists():
        print("❌ Database not found. Run youtube_monitor.py first to create it.")
        return 1
    
    video = get_video_by_id(args.video_id)
    
    if not video:
        print(f"❌ Video with ID '{args.video_id}' not found.")
        return 1
    
    print("\n" + format_video(video, show_full=True))
    return 0

def list_command(args):
    """Handle list command (show recent videos)."""
    if not DB_PATH.exists():
        print("❌ Database not found. Run youtube_monitor.py first to create it.")
        return 1
    
    results = search_videos(
        from_date=args.from_date,
        channel=args.channel,
        limit=args.limit
    )
    
    if not results:
        print("📭 No videos found.")
        return 0
    
    print(f"\n📋 Recent videos ({len(results)}):\n")
    
    for i, video in enumerate(results, 1):
        print(f"{i}. [{video['published_date']}] {video['video_title']}")
        print(f"   Channel: {video['channel_name']}")
        print(f"   ID: {video['video_id']}")
        print()
    
    print("💡 Use 'query_db.py get <video_id>' to see full summary")
    return 0

def main():
    parser = argparse.ArgumentParser(
        description="Query YouTube Research Database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for videos about Tesla
  python query_db.py search TSLA
  
  # Search with date filter
  python query_db.py search "artificial intelligence" --from 2026-01-01
  
  # Search in specific channel
  python query_db.py search stock --channel "Influencer 1"
  
  # Show full summary
  python query_db.py search NVDA --full
  
  # Get specific video by ID
  python query_db.py get xsoAkbIhM4w
  
  # List recent videos
  python query_db.py list --limit 20
  
  # Show database stats
  python query_db.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search videos')
    search_parser.add_argument('query', help='Search term (searches title, summary, topics, etc.)')
    search_parser.add_argument('--from', dest='from_date', help='Filter videos from this date (YYYY-MM-DD)')
    search_parser.add_argument('--channel', help='Filter by channel name')
    search_parser.add_argument('--limit', type=int, default=10, help='Maximum results (default: 10)')
    search_parser.add_argument('--full', action='store_true', help='Show full summaries')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get video by ID')
    get_parser.add_argument('video_id', help='YouTube video ID')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List recent videos')
    list_parser.add_argument('--from', dest='from_date', help='Filter videos from this date (YYYY-MM-DD)')
    list_parser.add_argument('--channel', help='Filter by channel name')
    list_parser.add_argument('--limit', type=int, default=20, help='Maximum results (default: 20)')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Route to appropriate handler
    if args.command == 'search':
        return search_command(args)
    elif args.command == 'get':
        return get_command(args)
    elif args.command == 'list':
        return list_command(args)
    elif args.command == 'stats':
        return stats_command(args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())

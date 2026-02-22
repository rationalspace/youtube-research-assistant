"""
Database schema for YouTube Research Assistant
Creates and manages the SQLite database for video summaries
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "research.db"

def init_database():
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create videos table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE NOT NULL,
            channel_name TEXT NOT NULL,
            video_title TEXT NOT NULL,
            video_url TEXT NOT NULL,
            published_date TEXT NOT NULL,
            processed_date TEXT NOT NULL,
            source_type TEXT NOT NULL,
            summary_text TEXT NOT NULL,
            key_topics TEXT,
            recommendations TEXT,
            action_items TEXT,
            duration_seconds INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create index for faster searches
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_channel_name ON videos(channel_name)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_published_date ON videos(published_date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_video_id ON videos(video_id)
    """)
    
    # Create full-text search virtual table
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS videos_fts USING fts5(
            video_title,
            summary_text,
            key_topics,
            recommendations,
            action_items,
            content=videos,
            content_rowid=id
        )
    """)
    
    # Create triggers to keep FTS table in sync
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS videos_ai AFTER INSERT ON videos BEGIN
            INSERT INTO videos_fts(rowid, video_title, summary_text, key_topics, recommendations, action_items)
            VALUES (new.id, new.video_title, new.summary_text, new.key_topics, new.recommendations, new.action_items);
        END
    """)
    
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS videos_ad AFTER DELETE ON videos BEGIN
            DELETE FROM videos_fts WHERE rowid = old.id;
        END
    """)
    
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS videos_au AFTER UPDATE ON videos BEGIN
            DELETE FROM videos_fts WHERE rowid = old.id;
            INSERT INTO videos_fts(rowid, video_title, summary_text, key_topics, recommendations, action_items)
            VALUES (new.id, new.video_title, new.summary_text, new.key_topics, new.recommendations, new.action_items);
        END
    """)
    
    conn.commit()
    conn.close()
    
    print(f"✓ Database initialized at {DB_PATH}")

def insert_video_summary(video_data):
    """
    Insert a video summary into the database.
    
    Args:
        video_data (dict): Dictionary containing video information
            - video_id: YouTube video ID
            - channel_name: Channel name
            - video_title: Video title
            - video_url: Full YouTube URL
            - published_date: ISO format date string
            - source_type: 'youtube_captions' or 'audio_transcription'
            - summary_text: Full summary text
            - key_topics: Comma-separated topics (optional)
            - recommendations: Recommendations text (optional)
            - action_items: Action items text (optional)
            - duration_seconds: Video duration in seconds (optional)
    
    Returns:
        int: Row ID of inserted record, or None if failed
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO videos (
                video_id, channel_name, video_title, video_url,
                published_date, processed_date, source_type, summary_text,
                key_topics, recommendations, action_items, duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            video_data['video_id'],
            video_data['channel_name'],
            video_data['video_title'],
            video_data['video_url'],
            video_data['published_date'],
            datetime.now().isoformat(),
            video_data.get('source_type', 'youtube_captions'),
            video_data['summary_text'],
            video_data.get('key_topics'),
            video_data.get('recommendations'),
            video_data.get('action_items'),
            video_data.get('duration_seconds')
        ))
        
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        
        return row_id
        
    except sqlite3.IntegrityError as e:
        # Video already exists (duplicate video_id)
        if "UNIQUE constraint failed" in str(e):
            print(f"    ⚠️  Video {video_data['video_id']} already in database, skipping")
            return None
        raise
    except Exception as e:
        print(f"    Error inserting into database: {e}")
        return None

def get_video_by_id(video_id):
    """Get a video summary by video ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

def search_videos(search_term=None, from_date=None, channel=None, limit=10):
    """
    Search videos with optional filters.
    
    Args:
        search_term: Text to search in title, summary, topics, etc.
        from_date: ISO date string to filter videos from this date onwards
        channel: Filter by channel name
        limit: Maximum number of results
    
    Returns:
        List of video dictionaries
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if search_term:
        # Use full-text search
        query = """
            SELECT v.* FROM videos v
            JOIN videos_fts ON v.id = videos_fts.rowid
            WHERE videos_fts MATCH ?
        """
        params = [search_term]
        
        if from_date:
            query += " AND v.published_date >= ?"
            params.append(from_date)
        
        if channel:
            query += " AND v.channel_name LIKE ?"
            params.append(f"%{channel}%")
        
        query += " ORDER BY v.published_date DESC LIMIT ?"
        params.append(limit)
        
    else:
        # No search term, just filter
        query = "SELECT * FROM videos WHERE 1=1"
        params = []
        
        if from_date:
            query += " AND published_date >= ?"
            params.append(from_date)
        
        if channel:
            query += " AND channel_name LIKE ?"
            params.append(f"%{channel}%")
        
        query += " ORDER BY published_date DESC LIMIT ?"
        params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_stats():
    """Get database statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {}
    
    # Total videos
    cursor.execute("SELECT COUNT(*) FROM videos")
    stats['total_videos'] = cursor.fetchone()[0]
    
    # Videos by channel
    cursor.execute("""
        SELECT channel_name, COUNT(*) as count
        FROM videos
        GROUP BY channel_name
        ORDER BY count DESC
    """)
    stats['by_channel'] = dict(cursor.fetchall())
    
    # Videos by source type
    cursor.execute("""
        SELECT source_type, COUNT(*) as count
        FROM videos
        GROUP BY source_type
    """)
    stats['by_source'] = dict(cursor.fetchall())
    
    # Date range
    cursor.execute("SELECT MIN(published_date), MAX(published_date) FROM videos")
    min_date, max_date = cursor.fetchone()
    stats['date_range'] = {'from': min_date, 'to': max_date}
    
    conn.close()
    return stats

if __name__ == "__main__":
    # Initialize database when run directly
    init_database()
    print("\n📊 Database Statistics:")
    stats = get_stats()
    print(f"Total videos: {stats['total_videos']}")
    print(f"Date range: {stats['date_range']['from']} to {stats['date_range']['to']}")
    print(f"\nBy channel: {stats['by_channel']}")
    print(f"By source: {stats['by_source']}")

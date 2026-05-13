#!/usr/bin/env python3
"""
YouTube Channel Monitor with AI Summaries
Monitors specified YouTube channels for new videos and sends daily email summaries.
"""

import os
import json
import time
import argparse
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from google import genai
from google.genai import errors as genai_errors
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import tempfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Database integration
from db_manager import init_database, insert_video_summary

# Legacy CONFIG dict — superseded by profiles/ YAML files.
# Kept for reference. Not used when --profile flag is provided.
CONFIG = {
    "channels": [
        {
            "url": "https://www.youtube.com/@parkevtatevosiancfa9544",
            "handle": "@parkevtatevosiancfa9544"
        },
        {
            "url": "https://www.youtube.com/@AkshatZayn",
            "handle": "@AkshatZayn"
        },
        {
            "url": "https://www.youtube.com/@FinTek",
            "handle": "@FinTek"
        },
        {
            "url": "https://www.youtube.com/@SahilBhadviya",
            "handle": "@SahilBhadviya"
        },
        {
            "url": "https://www.youtube.com/@TickerSymbolYOU",
            "handle": "@TickerSymbolYOU"
        }
    ],
    "check_interval_hours": 24,  # Check once per day
    "videos_per_channel": 3,  # Number of latest videos to check per channel
    "output_directory": "summaries",  # Where to save summary files
    "skip_no_transcript": False,  # Set to True to skip videos without transcripts (even with audio fallback)
    # Note: If YouTube captions are not available, the script will automatically download
    # the audio and use Gemini Flash to transcribe it. This may take longer (~30-60s per video).
    # All videos are included, even YouTube Shorts (under 60 seconds).
}

# Default processed videos file (overridden per-profile in __init__)
PROCESSED_VIDEOS_FILE = Path.home() / ".youtube_monitor_processed.json"

# Legacy SUMMARY_PROMPT — superseded by profile YAML's prompt field.
SUMMARY_PROMPT = """Analyze this financial video and provide a summary for a Product Leader. Do not omit any actionable data.

You MUST include:
1. Specific Tickers: List every stock or asset mentioned.
2. Price Info: Any price targets, current prices, or entry points mentioned.
3. The Rating: Did the creator give a Buy, Sell, or Hold rating? (If they didn't say it explicitly, summarize their 'vibe' or sentiment).
4. The 'Why': The core 2-minute investment thesis.
5. Actionability: What is the one thing I should do or watch after seeing this?

Video Title: {title}
Channel: {channel}
Published: {published}

Transcript:
{transcript}
"""


class QuotaExceededError(Exception):
    """Raised when a YouTube or Gemini API quota is exhausted."""
    pass


def _is_rate_limit_error(exc):
    """Return True ONLY if exc is a pure per-minute rate limit with no daily quota violation.

    When the daily quota is exhausted the error often includes BOTH a per-day AND a
    per-minute violation in its violations list.  Checking for 'perminute' alone would
    misclassify a fatal daily-limit error as a recoverable rate limit, causing the script
    to retry 4×65s per video before giving up silently.

    Rule: a per-minute violation is only retryable when there is NO concurrent per-day
    violation in the same error.
    """
    msg = str(exc).lower()
    # Matches both old snake_case (quota_id) and new camelCase (quotaId) SDK formats
    has_per_minute = 'perminute' in msg or 'per_minute' in msg
    # Any of these strings indicate the DAILY quota bucket is also exhausted
    has_per_day = 'perday' in msg or 'per_day' in msg or 'dailylimit' in msg
    return has_per_minute and not has_per_day


def _is_quota_error(exc):
    """Return True if exc is a DAILY quota exhaustion (not recoverable until tomorrow).

    Deliberately excludes per-minute rate limits — those are handled by
    _is_rate_limit_error() and retried with a short sleep inside _gemini_call_with_retry().
    """
    # Per-minute rate limits are recoverable — don't treat them as fatal quota exhaustion
    if _is_rate_limit_error(exc):
        return False
    # YouTube Data API: HttpError 403 with daily quota reason
    if isinstance(exc, HttpError):
        if exc.resp.status == 403 and any(
            kw in str(exc).lower()
            for kw in ('quotaexceeded', 'dailylimitexceeded', 'ratelimitexceeded')
        ):
            return True
    # New google-genai SDK: ClientError with HTTP 429 that is NOT a pure per-minute limit
    # (per-minute was already excluded by the _is_rate_limit_error() guard above)
    if isinstance(exc, genai_errors.ClientError) and getattr(exc, 'code', None) == 429:
        return True
    # Old google-generativeai SDK: ResourceExhausted
    try:
        from google.api_core.exceptions import ResourceExhausted
        if isinstance(exc, ResourceExhausted):
            return True
    except ImportError:
        pass
    # Fallback: string match for daily-limit keywords only.
    # 'perday' catches quotaId: "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
    msg = str(exc).lower()
    return any(kw in msg for kw in ('quotaexceeded', 'dailylimitexceeded',
                                     'ratelimitexceeded', 'dailylimit', 'perday'))


def _is_transient_error(exc):
    """Return True if exc is a temporary server/network error worth retrying.

    Covers:
    - Gemini 503 UNAVAILABLE (model temporarily overloaded — usually resolves in <60s)
    - OS-level network errors: ECONNRESET (54) and EPIPE (32) from a freshly woken Mac
    - Wrapped httpx/requests errors with the same underlying cause
    """
    # Gemini 503 via new google-genai SDK (ServerError)
    if isinstance(exc, genai_errors.ServerError) and getattr(exc, 'code', None) == 503:
        return True
    # OS-level: Broken pipe (32) or Connection reset by peer (54)
    if getattr(exc, 'errno', None) in (32, 54):
        return True
    # String fallback for exceptions wrapped by httpx / urllib3 / requests
    msg = str(exc).lower()
    if '503' in msg and ('unavailable' in msg or 'high demand' in msg):
        return True
    if 'connection reset' in msg or 'broken pipe' in msg:
        return True
    return False


def load_profile(profile_name):
    """Load a profile YAML file from profiles/{name}.yaml.

    Returns a dict with keys: channels, prompt, enable_reading_queue.
    Exits with a clear error message if the file is missing or malformed.
    """
    profiles_dir = Path(__file__).parent / "profiles"
    profile_path = profiles_dir / f"{profile_name}.yaml"

    if not profile_path.exists():
        available = sorted(p.stem for p in profiles_dir.glob("*.yaml")) if profiles_dir.exists() else []
        print(f"\nError: Profile '{profile_name}' not found at {profile_path}")
        if available:
            print(f"Available profiles: {', '.join(available)}")
        else:
            print(f"No profiles found in: {profiles_dir}")
        raise SystemExit(1)

    with open(profile_path, 'r') as f:
        config = yaml.safe_load(f)

    for key in ('channels', 'prompt'):
        if key not in config:
            print(f"\nError: Profile '{profile_name}' missing required key: '{key}'")
            raise SystemExit(1)

    config.setdefault('enable_reading_queue', False)
    return config


class YouTubeMonitor:
    def __init__(self, profile_name, profile_config):
        # Store profile identity and config
        self.profile_name = profile_name
        self.profile_config = profile_config

        # Extract profile-specific values
        self.channels = profile_config['channels']
        self.summary_prompt = profile_config['prompt']
        self.enable_reading_queue = profile_config.get('enable_reading_queue', False)

        # Profile-specific processed videos tracking file
        self.processed_videos_file = Path.home() / f".youtube_monitor_processed_{profile_name}.json"

        # Profile-specific output directory
        self.output_dir = Path("summaries") / profile_name
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load API keys from environment variables
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.gmail_user = os.getenv('GMAIL_USER')
        self.gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL', self.gmail_user)

        if not all([self.youtube_api_key, self.gemini_api_key,
                   self.gmail_user, self.gmail_app_password]):
            raise ValueError("Missing required environment variables. See setup instructions.")

        self.youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)

        # Configure Gemini via the new google-genai SDK (google.generativeai is deprecated)
        self.client = genai.Client(api_key=self.gemini_api_key)
        # gemini-2.5-flash-lite: 20 req/day free. gemini-2.0-flash has limit:0 on this key.
        self.model_name = 'gemini-2.5-flash-lite'

        self.processed_videos = self._load_processed_videos()

        # Initialize database
        init_database()
    
    def _load_processed_videos(self):
        """Load the set of already processed video IDs."""
        if self.processed_videos_file.exists():
            with open(self.processed_videos_file, 'r') as f:
                return set(json.load(f))
        return set()

    def _save_processed_videos(self):
        """Save the set of processed video IDs."""
        with open(self.processed_videos_file, 'w') as f:
            json.dump(list(self.processed_videos), f)
    
    def get_channel_id(self, handle):
        """Get channel ID from handle, with retry on transient network errors."""
        handle_clean = handle.replace('@', '')
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                request = self.youtube.search().list(
                    part='snippet',
                    q=handle_clean,
                    type='channel',
                    maxResults=1
                )
                response = request.execute()
                if response['items']:
                    return response['items'][0]['snippet']['channelId']
                return None
            except Exception as e:
                if _is_quota_error(e):
                    raise QuotaExceededError(f"YouTube API quota exceeded: {e}") from e
                if _is_transient_error(e) and attempt < max_retries:
                    wait = 15 * (attempt + 1)  # 15s, 30s, 45s
                    print(f"    ⏳ Network error getting channel ID — waiting {wait}s "
                          f"({attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                    continue
                print(f"Error getting channel ID for {handle}: {e}")
                return None
        return None
    
    def get_latest_videos(self, channel_id, count=3):
        """Get the latest N videos from a channel, with retry on transient network errors."""
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                # Fetch more videos than needed to account for filtering
                request = self.youtube.search().list(
                    part='snippet',
                    channelId=channel_id,
                    type='video',
                    order='date',
                    maxResults=15  # Fetch extra to account for filtering
                )
                response = request.execute()

                valid_videos = []
                video_ids = []

                # First pass: collect video IDs
                for item in response.get('items', []):
                    video_ids.append(item['id']['videoId'])

                if not video_ids:
                    return []

                # Get video details including duration
                video_details_request = self.youtube.videos().list(
                    part='contentDetails,status,snippet',
                    id=','.join(video_ids)
                )
                video_details = video_details_request.execute()

                # Second pass: filter videos
                for video in video_details.get('items', []):
                    # Skip if we already have enough videos
                    if len(valid_videos) >= count:
                        break

                    video_id = video['id']

                    # Get duration in ISO 8601 format (e.g., "PT15M33S")
                    duration_str = video['contentDetails']['duration']
                    duration_seconds = self._parse_duration(duration_str)

                    # Note: We're keeping ALL videos now, including Shorts (even under 60s)

                    # Check if video is private or unlisted
                    privacy_status = video['status'].get('privacyStatus', 'public')
                    if privacy_status != 'public':
                        print(f"    ⏭️  Skipping {privacy_status} video: {video['snippet']['title']}")
                        continue

                    # Note: We removed keyword-based member-only detection as it was too aggressive.
                    # YouTube API doesn't directly expose member-only status in a reliable way.
                    # If a video is truly members-only, we'll find out when we try to get the transcript/audio.
                    # At that point, we can skip it or mark it accordingly.

                    # Video passed all filters
                    valid_videos.append({
                        'id': video_id,
                        'title': video['snippet']['title'],
                        'published': video['snippet']['publishedAt'],
                        'channel': video['snippet']['channelTitle'],
                        'description': video['snippet'].get('description', ''),
                        'duration_seconds': duration_seconds
                    })

                return valid_videos

            except Exception as e:
                if _is_quota_error(e):
                    raise QuotaExceededError(f"YouTube API quota exceeded: {e}") from e
                if _is_transient_error(e) and attempt < max_retries:
                    wait = 15 * (attempt + 1)  # 15s, 30s, 45s
                    print(f"    ⏳ Network error getting videos — waiting {wait}s "
                          f"({attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                    continue
                print(f"Error getting videos for channel {channel_id}: {e}")
                import traceback
                traceback.print_exc()
                return []
        return []
    
    def _parse_duration(self, duration_str):
        """Parse ISO 8601 duration format (e.g., 'PT15M33S') to seconds."""
        import re
        
        # Pattern to match hours, minutes, and seconds
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_str)
        
        if not match:
            return 0
        
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        seconds = int(match.group(3)) if match.group(3) else 0
        
        return hours * 3600 + minutes * 60 + seconds
    
    def download_audio(self, video_id):
        """Download audio from YouTube video to temporary file."""
        try:
            # Create temporary directory for audio files
            temp_dir = Path(tempfile.gettempdir()) / "youtube_monitor_audio"
            temp_dir.mkdir(exist_ok=True)
            
            output_path = temp_dir / f"{video_id}.mp3"
            
            # Configure yt-dlp options
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': str(temp_dir / f"{video_id}.%(ext)s"),
                'quiet': True,
                'no_warnings': True,
            }
            
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            print(f"    Downloading audio from video...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if output_path.exists():
                print(f"    ✓ Audio downloaded: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
                return str(output_path)
            else:
                print(f"    ⚠️ Audio file not found after download")
                return None
                
        except Exception as e:
            error_msg = str(e).lower()
            if 'members only' in error_msg or 'private' in error_msg or 'unavailable' in error_msg:
                print(f"    ⚠️ Video is restricted (members-only or private)")
                return "MEMBERS_ONLY"
            print(f"    Error downloading audio: {e}")
            return None
    
    def _gemini_call_with_retry(self, *args, max_retries=4, **kwargs):
        """Call self.model.generate_content with automatic retry on per-minute rate limits.

        The Gemini free tier allows 5 requests/minute. With 5 channels × 3 videos the
        script easily exceeds this. When a per-minute 429 is detected we wait 65s and
        retry rather than aborting the whole run. After max_retries attempts the last
        exception is re-raised so the caller can handle it normally.
        """
        contents = args[0] if args else kwargs.get('contents')
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                return self.client.models.generate_content(
                    model=self.model_name, contents=contents)
            except Exception as e:
                # Daily quota exhaustion — raise immediately, do NOT retry.
                # Let the caller's _is_quota_error() check handle it.
                if _is_quota_error(e):
                    raise
                if _is_rate_limit_error(e) and attempt < max_retries:
                    wait = 65
                    print(f"    ⏳ Gemini rate limit hit — waiting {wait}s before retry "
                          f"({attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                    last_exc = e
                    continue
                # 503 overloaded or transient network error — retry with backoff
                if _is_transient_error(e) and attempt < max_retries:
                    wait = 30 * (attempt + 1)  # 30s, 60s, 90s, 120s
                    print(f"    ⏳ Transient error ({type(e).__name__}) — waiting {wait}s "
                          f"before retry ({attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                    last_exc = e
                    continue
                raise
        raise last_exc  # should never reach here, but satisfies type checkers

    def transcribe_audio_with_gemini(self, audio_path):
        """Transcribe audio file using Gemini Flash."""
        try:
            print(f"    Transcribing audio with Gemini Flash...")
            
            # Upload audio file to Gemini (new SDK: client.files.upload)
            audio_file = self.client.files.upload(file=audio_path)

            # Create prompt for transcription
            prompt = """Please transcribe this audio completely and accurately.

Provide the full transcript of everything said in the audio. Do not summarize - transcribe word-for-word.
Return only the transcript text, nothing else."""

            # Generate transcription (retries automatically on per-minute rate limits)
            response = self._gemini_call_with_retry([prompt, audio_file])
            transcript = response.text

            # Clean up uploaded file from Gemini (new SDK: client.files.delete)
            self.client.files.delete(name=audio_file.name)
            
            print(f"    ✓ Transcription complete ({len(transcript)} characters)")
            return transcript
            
        except Exception as e:
            if _is_quota_error(e):
                raise QuotaExceededError(f"Gemini API quota exceeded: {e}") from e
            print(f"    Error transcribing audio with Gemini: {e}")
            return None
    
    def get_transcript(self, video_id):
        """Get transcript for a video, trying multiple methods including audio transcription."""
        # First, try to get YouTube captions
        try:
            # Try to get transcript in multiple languages
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            
            # First try to find manually created transcripts
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
                transcript_data = transcript.fetch()
            except:
                # Fall back to auto-generated transcripts
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                    transcript_data = transcript.fetch()
                except:
                    # Try any available transcript and translate to English
                    try:
                        for transcript in transcript_list:
                            transcript_data = transcript.translate('en').fetch()
                            break
                    except:
                        # No captions available - will try audio fallback below
                        transcript_data = None
            
            if transcript_data:
                transcript_text = ' '.join([entry.text for entry in transcript_data])
                print(f"    ✓ Transcript retrieved from YouTube captions")
                self._last_transcript_method = 'youtube_captions'
                return transcript_text
            
        except Exception as e:
            error_msg = str(e).lower()
            # Check if error indicates members-only content
            if 'members only' in error_msg or 'join this channel' in error_msg or 'premium' in error_msg:
                print(f"    ⚠️  Video appears to be members-only: {error_msg}")
                return "MEMBERS_ONLY"
            print(f"    No captions available, will try audio transcription...")
        
        # Fallback: Try audio transcription with Gemini
        print(f"    📥 No captions found - attempting audio transcription fallback...")
        
        audio_path = self.download_audio(video_id)
        
        if audio_path == "MEMBERS_ONLY":
            return "MEMBERS_ONLY"
        
        if not audio_path:
            print(f"    ⚠️  Could not download audio")
            return None
        
        # Transcribe the audio with Gemini
        transcript = self.transcribe_audio_with_gemini(audio_path)
        
        # Clean up audio file
        try:
            Path(audio_path).unlink()
            print(f"    ✓ Cleaned up audio file")
        except:
            pass
        
        if transcript:
            self._last_transcript_method = 'audio_transcription'
        
        return transcript
    
    def generate_summary(self, video):
        """Generate AI summary for a video."""
        transcript = self.get_transcript(video['id'])
        
        # Check if video is members-only
        if transcript == "MEMBERS_ONLY":
            return "SKIP_MEMBERS_ONLY"
        
        # If no transcript, try to use the video description
        if not transcript:
            print(f"    No transcript available, using video description instead...")
            
            if video['description'] and len(video['description']) > 50:
                # Use description for analysis
                prompt = f"""Analyze this financial video based on its description and provide a summary for a Product Leader.

Video Title: {video['title']}
Channel: {video['channel']}
Published: {video['published']}

Description:
{video['description']}

Based on this information, please provide:
1. Specific Tickers: List any stocks or assets you can identify from the title/description
2. Price Info: Any price targets or levels mentioned
3. The Rating: What sentiment does the title/description suggest? (Bullish/Bearish/Neutral)
4. The 'Why': What appears to be the main topic or thesis based on available info
5. Actionability: Recommend watching the video at the URL below for full details

Note: This summary is based on limited information (title and description only) since the video transcript was not available.

VIDEO URL: https://youtube.com/watch?v={video['id']}
"""
                try:
                    response = self._gemini_call_with_retry(prompt)
                    summary = "⚠️ LIMITED INFO - Transcript not available, summary based on description only:\n\n" + response.text
                    return summary
                except Exception as e:
                    if _is_quota_error(e):
                        raise QuotaExceededError(f"Gemini API quota exceeded: {e}") from e
                    print(f"    Error generating description-based summary: {e}")
            
            # Last resort: return basic info
            return f"""⚠️ Unable to generate detailed summary - transcript and description not available

This video was recently published and may not have captions yet. Try checking back later or watch it directly:

Title: {video['title']}
Channel: {video['channel']}
URL: https://youtube.com/watch?v={video['id']}

Recommendation: Watch the video directly to get the full analysis."""
        
        # Transcript is available - do full analysis
        max_chars = 100000
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "... [transcript truncated]"
        
        prompt = self.summary_prompt.format(
            title=video['title'],
            channel=video['channel'],
            published=video['published'],
            transcript=transcript
        )
        
        try:
            response = self._gemini_call_with_retry(prompt)
            summary = response.text
            return summary
        except Exception as e:
            if _is_quota_error(e):
                raise QuotaExceededError(f"Gemini API quota exceeded: {e}") from e
            print(f"Error generating summary for video {video['id']}: {e}")
            return f"⚠️ Error generating summary: {str(e)}"
    
    def save_to_file(self, content, filename=None):
        """Save summary to a file."""
        try:
            if filename is None:
                # Generate filename with timestamp
                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                filename = f"summary_{timestamp}.txt"
            
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✓ Summary saved to: {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"Error saving to file: {e}")
            return None
    
    def send_email(self, subject, body):
        """Send email report."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.gmail_user
            msg['To'] = self.recipient_email
            
            # Create text part
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Send email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.gmail_user, self.gmail_app_password)
                server.send_message(msg)
            
            print(f"✓ Email sent successfully to {self.recipient_email}")
            return True
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            print(f"   Check your GMAIL_USER and GMAIL_APP_PASSWORD settings")
            return False
    
    def check_channels(self):
        """Check all channels for new videos and generate report.

        Quota-safe: if the Gemini daily quota is exhausted mid-run, any summaries
        already generated are still emailed and saved rather than being discarded.
        A QuotaExceededError is only re-raised when zero summaries were produced.
        """
        print(f"\n{'='*60}")
        print(f"YouTube Monitor Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        all_summaries = []
        new_videos_found = False
        quota_exhausted = False  # set True when we hit the daily API limit mid-run

        for channel_config in self.channels:
            if quota_exhausted:
                break

            handle = channel_config['handle']
            print(f"Checking channel: {handle}")

            # YouTube API quota failure → stop immediately
            try:
                channel_id = self.get_channel_id(handle)
            except QuotaExceededError:
                print(f"  🚫 YouTube API quota exhausted — stopping early\n")
                quota_exhausted = True
                break

            if not channel_id:
                print(f"  ⚠️ Could not find channel ID for {handle}")
                continue

            videos_per_channel = self.profile_config.get('videos_per_channel', 2)
            try:
                videos = self.get_latest_videos(channel_id, count=videos_per_channel)
            except QuotaExceededError:
                print(f"  🚫 YouTube API quota exhausted — stopping early\n")
                quota_exhausted = True
                break

            print(f"  Found {len(videos)} valid video(s) (after filtering)\n")

            for video in videos:
                if video['id'] in self.processed_videos:
                    print(f"  ⏭️  Already processed: {video['title']}")
                    continue

                new_videos_found = True
                print(f"  🆕 New video: {video['title']}")
                print(f"      Duration: {video['duration_seconds']}s")
                print(f"  📝 Generating summary...")

                # Check if video has transcript (if skip_no_transcript is enabled)
                if self.profile_config.get('skip_no_transcript', False):
                    transcript = self.get_transcript(video['id'])
                    if not transcript:
                        print(f"  ⏭️  Skipping (no transcript available)")
                        self.processed_videos.add(video['id'])
                        continue

                # Gemini quota failure → stop generating, send what we have
                try:
                    summary = self.generate_summary(video)
                except QuotaExceededError:
                    print(f"  🚫 Gemini quota exhausted — stopping after "
                          f"{len(all_summaries)} summary(ies)\n")
                    quota_exhausted = True
                    break  # inner loop — outer loop checks quota_exhausted

                # Skip if video is members-only
                if summary == "SKIP_MEMBERS_ONLY":
                    print(f"  ⏭️  Skipping members-only video\n")
                    self.processed_videos.add(video['id'])
                    continue

                # Determine source type based on how we got the transcript
                transcript_method = getattr(self, '_last_transcript_method', 'youtube_captions')

                video_summary = f"""
{'='*60}
📺 {video['title']}
{'='*60}
Channel: {video['channel']}
Published: {video['published']}
Duration: {video['duration_seconds']}s
URL: https://youtube.com/watch?v={video['id']}

{summary}
"""
                all_summaries.append(video_summary)
                self.processed_videos.add(video['id'])

                # Save to database
                db_data = {
                    'video_id': video['id'],
                    'channel_name': video['channel'],
                    'video_title': video['title'],
                    'video_url': f"https://youtube.com/watch?v={video['id']}",
                    'published_date': video['published'],
                    'source_type': transcript_method,
                    'summary_text': summary,
                    'duration_seconds': video.get('duration_seconds', 0),
                    'key_topics': None,
                    'recommendations': None,
                    'action_items': None
                }

                row_id = insert_video_summary(db_data)
                if row_id:
                    print(f"  💾 Saved to database (ID: {row_id})")

                print(f"  ✓ Summary generated\n")

        # Always persist the videos we successfully processed, even if we stopped early
        self._save_processed_videos()

        if new_videos_found and all_summaries:
            timestamp = datetime.now().strftime('%Y-%m-%d')
            filename = f"daily_summary_{timestamp}.txt"

            quota_note = (
                "\n⚠️  Note: Gemini API daily quota was exhausted mid-run. "
                "This digest covers only the channels processed before the limit was hit. "
                "Remaining channels will be included in tomorrow's email.\n"
                if quota_exhausted else ""
            )

            content = f"""Daily YouTube Video Summary - Profile: {self.profile_name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{quota_note}
Found {len(all_summaries)} new video(s):

{''.join(all_summaries)}

---
Automated report from YouTube Monitor (profile: {self.profile_name}).
"""

            self.save_to_file(content, filename)

            subject_suffix = " ⚠️ Partial — quota hit" if quota_exhausted else ""
            subject = (f"[{self.profile_name}] 📊 Daily Video Summary "
                       f"- {len(all_summaries)} New Video(s){subject_suffix}")
            self.send_email(subject, content)

        elif quota_exhausted and not all_summaries:
            # Quota hit before a single summary was produced — nothing useful to send
            raise QuotaExceededError(
                "Gemini quota exhausted before any summaries could be generated"
            )
        else:
            print("\n📭 No new videos found.")

        print(f"\n{'='*60}")
        print("Check complete!")
        print(f"{'='*60}\n")
    
    def run_forever(self):
        """Run the monitor continuously."""
        check_interval = self.profile_config.get('check_interval_hours', 24)
        print("🚀 YouTube Monitor started!")
        print(f"Profile: {self.profile_name}")
        print(f"Checking every {check_interval} hours")
        print(f"Monitoring {len(self.channels)} channels")
        print("Press Ctrl+C to stop\n")

        while True:
            try:
                self.check_channels()

                # Wait until next check
                next_check = datetime.now() + timedelta(hours=check_interval)
                print(f"💤 Next check scheduled for: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Sleeping for {check_interval} hours...\n")

                time.sleep(check_interval * 3600)
            
            except KeyboardInterrupt:
                print("\n\n👋 YouTube Monitor stopped by user.")
                break
            except QuotaExceededError as e:
                # Stop immediately — don't retry hourly, quota won't recover until midnight Pacific.
                # Sleep the full check interval so the next attempt aligns with the normal schedule.
                next_check = datetime.now() + timedelta(hours=check_interval)
                print(f"\n🚫 API quota exhausted: {e}")
                print(f"   No email will be sent for this run.")
                print(f"   Resuming at next scheduled check: {next_check.strftime('%Y-%m-%d %H:%M:%S')}\n")
                time.sleep(check_interval * 3600)
            except Exception as e:
                print(f"\n⚠️ Error during check: {e}")
                print("Waiting 1 hour before retry...\n")
                time.sleep(3600)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='YouTube Channel Monitor with AI Summaries')
    parser.add_argument(
        '--profile',
        required=True,
        metavar='PROFILE_NAME',
        help='Profile to use (e.g. finance, pm_ai). Loads from profiles/{name}.yaml'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run a single check and exit instead of running continuously'
    )
    args = parser.parse_args()

    profile_config = load_profile(args.profile)

    try:
        monitor = YouTubeMonitor(args.profile, profile_config)
        if args.once:
            monitor.check_channels()
        else:
            monitor.run_forever()
    except QuotaExceededError as e:
        print(f"\n🚫 API quota exhausted: {e}")
        print("   No email sent. Re-run tomorrow when quota resets.")
        return 0
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}\n")
        print("Please set the following environment variables:")
        print("  - YOUTUBE_API_KEY: Your YouTube Data API v3 key")
        print("  - GEMINI_API_KEY: Your Google Gemini API key")
        print("  - GMAIL_USER: Your Gmail address")
        print("  - GMAIL_APP_PASSWORD: Your Gmail app password")
        print("  - RECIPIENT_EMAIL: Email to receive reports (optional, defaults to GMAIL_USER)")
        return 1
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

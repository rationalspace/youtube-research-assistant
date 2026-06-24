#!/usr/bin/env python3
"""
Unit tests for YouTubeMonitor.check_channels() error handling.

Covers the fix where a video whose summary failed with a transient error
(Gemini 503, connection reset, etc.) must NOT be:
  - included in the emailed digest
  - marked as processed
  - saved to the database

...so the next scheduled run retries it instead of permanently skipping it.

Run with: python -m unittest test_check_channels.py -v
No live API calls, no network access, no real credentials required.
"""

import unittest
from unittest.mock import patch, MagicMock

from youtube_monitor import YouTubeMonitor


def make_monitor(channels, videos_per_channel=2):
    """Construct a YouTubeMonitor without running __init__ (no real API clients/creds)."""
    monitor = YouTubeMonitor.__new__(YouTubeMonitor)
    monitor.profile_name = "test_profile"
    monitor.profile_config = {
        "channels": channels,
        "videos_per_channel": videos_per_channel,
    }
    monitor.channels = channels
    monitor.processed_videos = set()
    monitor.enable_reading_queue = False
    return monitor


def make_video(video_id, title="Some Video", duration=300):
    return {
        "id": video_id,
        "title": title,
        "channel": "Test Channel",
        "published": "2026-05-12",
        "description": "",
        "duration_seconds": duration,
    }


class TestCheckChannelsTransientErrorHandling(unittest.TestCase):
    def setUp(self):
        self.channels = [{"handle": "@testchannel", "url": "https://youtube.com/@testchannel"}]
        self.monitor = make_monitor(self.channels)

    @patch("youtube_monitor.insert_video_summary")
    def test_failed_summary_excluded_from_email_and_not_persisted(self, mock_insert):
        """A video whose generate_summary() returns the error placeholder must be
        skipped entirely: not emailed, not marked processed, not saved to DB."""
        failed_video = make_video("FAIL123", title="Video That Errors")

        self.monitor.get_channel_id = MagicMock(return_value="UC_fake_channel_id")
        self.monitor.get_latest_videos = MagicMock(return_value=[failed_video])
        self.monitor.generate_summary = MagicMock(
            return_value="⚠️ Error generating summary: 503 UNAVAILABLE. Model overloaded."
        )
        self.monitor._save_processed_videos = MagicMock()
        self.monitor.save_to_file = MagicMock()
        self.monitor.send_email = MagicMock()

        self.monitor.check_channels()

        # Must NOT have been emailed
        self.monitor.send_email.assert_not_called()
        # Must NOT be marked processed (so next run retries it)
        self.assertNotIn("FAIL123", self.monitor.processed_videos)
        # Must NOT be persisted to the DB
        mock_insert.assert_not_called()

    @patch("youtube_monitor.insert_video_summary", return_value=1)
    def test_successful_summary_is_emailed_and_persisted(self, mock_insert):
        """A video that summarizes successfully should still be emailed, marked
        processed, and saved to the DB exactly as before this fix."""
        good_video = make_video("GOOD456", title="Video That Works")

        self.monitor.get_channel_id = MagicMock(return_value="UC_fake_channel_id")
        self.monitor.get_latest_videos = MagicMock(return_value=[good_video])
        self.monitor.generate_summary = MagicMock(return_value="This is a real summary.")
        self.monitor._save_processed_videos = MagicMock()
        self.monitor.save_to_file = MagicMock()
        self.monitor.send_email = MagicMock()

        self.monitor.check_channels()

        self.monitor.send_email.assert_called_once()
        self.assertIn("GOOD456", self.monitor.processed_videos)
        mock_insert.assert_called_once()
        # Sanity-check the emailed digest actually contains the good video's summary
        _, args, kwargs = self.monitor.send_email.mock_calls[0]
        body = args[1] if len(args) > 1 else kwargs.get("body", "")
        self.assertIn("This is a real summary.", body)

    @patch("youtube_monitor.insert_video_summary", return_value=1)
    def test_mixed_batch_only_failed_video_is_excluded(self, mock_insert):
        """With one failing and one succeeding video in the same run, only the
        successful one should reach the email/DB; the failed one is skipped."""
        failed_video = make_video("FAIL789", title="Errors Out")
        good_video = make_video("GOOD789", title="Succeeds Fine")

        self.monitor.get_channel_id = MagicMock(return_value="UC_fake_channel_id")
        self.monitor.get_latest_videos = MagicMock(return_value=[failed_video, good_video])

        def fake_generate_summary(video):
            if video["id"] == "FAIL789":
                return "⚠️ Error generating summary: [Errno 54] Connection reset by peer"
            return "A working summary for the good video."

        self.monitor.generate_summary = MagicMock(side_effect=fake_generate_summary)
        self.monitor._save_processed_videos = MagicMock()
        self.monitor.save_to_file = MagicMock()
        self.monitor.send_email = MagicMock()

        self.monitor.check_channels()

        self.assertNotIn("FAIL789", self.monitor.processed_videos)
        self.assertIn("GOOD789", self.monitor.processed_videos)
        mock_insert.assert_called_once()  # only the good video was saved
        self.monitor.send_email.assert_called_once()

        _, args, kwargs = self.monitor.send_email.mock_calls[0]
        body = args[1] if len(args) > 1 else kwargs.get("body", "")
        self.assertIn("A working summary for the good video.", body)
        self.assertNotIn("Connection reset by peer", body)


if __name__ == "__main__":
    unittest.main()

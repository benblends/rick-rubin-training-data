#!/usr/bin/env python3
"""YouTube collector v2 - using yt-dlp for subtitle extraction"""

import json
import re
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import yt_dlp
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubeCollectorV2:
    """Collect YouTube transcripts using yt-dlp subtitle extraction."""
    
    def __init__(self):
        self.rick_rubin_channels = {
            'tetragrammaton': '@Tetragrammaton',  # Using @ handle
            'broken_record': '@BrokenRecordPodcast',
            'rick_beato': '@RickBeato',
        }
        
        # Configure yt-dlp for subtitle extraction
        self.ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'subtitleslangs': ['en'],
        }
    
    def collect_single(self, url: str) -> Optional[Dict]:
        """Collect transcript from a single YouTube video using yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Extract video info
                logger.info(f"Extracting info from: {url}")
                info = ydl.extract_info(url, download=False)
                
                # Get basic metadata
                video_id = info.get('id', '')
                title = info.get('title', '')
                channel = info.get('channel', '')
                duration = info.get('duration', 0)
                upload_date = info.get('upload_date', '')
                
                # Try to get subtitles
                transcript_text = ""
                
                # Check for manual subtitles first
                if 'subtitles' in info and 'en' in info['subtitles']:
                    sub_url = self._get_subtitle_url(info['subtitles']['en'])
                    if sub_url:
                        transcript_text = self._download_and_parse_subtitles(sub_url)
                
                # Fall back to automatic captions
                if not transcript_text and 'automatic_captions' in info:
                    if 'en' in info['automatic_captions']:
                        sub_url = self._get_subtitle_url(info['automatic_captions']['en'])
                        if sub_url:
                            transcript_text = self._download_and_parse_subtitles(sub_url)
                
                if not transcript_text:
                    logger.error(f"No subtitles found for {url}")
                    return None
                
                # Clean the transcript
                transcript_text = self._clean_subtitle_text(transcript_text)
                
                result = {
                    'video_id': video_id,
                    'url': url,
                    'title': title,
                    'channel': channel,
                    'upload_date': upload_date,
                    'duration': duration,
                    'transcript': transcript_text,
                    'word_count': len(transcript_text.split()),
                    'collected_at': datetime.now().isoformat(),
                }
                
                logger.info(f"Collected transcript: {title} ({result['word_count']} words)")
                return result
                
        except Exception as e:
            logger.error(f"Error collecting transcript from {url}: {e}")
            return None
    
    def _get_subtitle_url(self, subtitle_formats: List[Dict]) -> Optional[str]:
        """Get the best subtitle URL from available formats."""
        # Prefer json3 format
        for fmt in subtitle_formats:
            if fmt.get('ext') == 'json3':
                return fmt.get('url')
        
        # Fall back to srv3
        for fmt in subtitle_formats:
            if fmt.get('ext') == 'srv3':
                return fmt.get('url')
        
        # Fall back to any format
        if subtitle_formats:
            return subtitle_formats[0].get('url')
        
        return None
    
    def _download_and_parse_subtitles(self, url: str) -> str:
        """Download and parse subtitles from URL."""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse JSON3 format
            if 'json3' in url:
                data = response.json()
                events = data.get('events', [])
                
                text_parts = []
                for event in events:
                    if 'segs' in event:
                        for seg in event['segs']:
                            if 'utf8' in seg:
                                text_parts.append(seg['utf8'])
                
                return ' '.join(text_parts)
            
            # Parse other formats (treat as text)
            else:
                return response.text
                
        except Exception as e:
            logger.error(f"Error downloading subtitles: {e}")
            return ""
    
    def _clean_subtitle_text(self, text: str) -> str:
        """Clean subtitle text."""
        # Remove newlines and extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove music/sound annotations
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        
        # Fix common issues
        text = text.replace('&#39;', "'")
        text = text.replace('&quot;', '"')
        text = text.replace('&amp;', '&')
        
        return text.strip()
    
    def get_channel_videos(self, channel_handle: str, max_results: int = 50) -> List[Dict]:
        """Get videos from a channel using its @ handle."""
        url = f"https://www.youtube.com/{channel_handle}/videos"
        
        ydl_opts = {
            **self.ydl_opts,
            'extract_flat': True,
            'playlistend': max_results,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                entries = info.get('entries', [])[:max_results]
                
                videos = []
                for entry in entries:
                    if entry:
                        videos.append({
                            'video_id': entry.get('id'),
                            'title': entry.get('title'),
                            'url': f"https://youtube.com/watch?v={entry.get('id')}",
                            'duration': entry.get('duration'),
                            'upload_date': entry.get('upload_date'),
                        })
                
                logger.info(f"Found {len(videos)} videos from {channel_handle}")
                return videos
                
            except Exception as e:
                logger.error(f"Error fetching channel videos: {e}")
                return []


def main():
    """Test the new collector."""
    collector = YouTubeCollectorV2()
    
    # Test with Joe Rogan episode
    test_url = "https://www.youtube.com/watch?v=uFiR3nVtYKY"
    print(f"\nTesting with: {test_url}")
    
    result = collector.collect_single(test_url)
    if result:
        print(f"\nSuccess!")
        print(f"Title: {result['title']}")
        print(f"Channel: {result['channel']}")
        print(f"Words: {result['word_count']}")
        print(f"Sample: {result['transcript'][:200]}...")
    else:
        print("Failed to collect transcript")


if __name__ == "__main__":
    main()
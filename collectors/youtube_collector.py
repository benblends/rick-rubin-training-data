#!/usr/bin/env python3
"""YouTube collector for Rick Rubin content, focusing on Tetragrammaton podcast."""

import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubeCollector:
    """Collect YouTube transcripts from Rick Rubin content."""
    
    def __init__(self):
        self.rick_rubin_channels = {
            'tetragrammaton': 'UCU1dNBOCJnl54mLaIR-A-9Q',  # Corrected channel ID
            'broken_record': 'UCdBY0otOhDpjpvxDLPJqsOg',  # Broken Record podcast
            # Add more channels as discovered
        }
        
        # Configure yt-dlp
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
    
    def get_channel_videos(self, channel_id: str, max_results: int = 50) -> List[Dict]:
        """Get list of videos from a channel."""
        url = f"https://www.youtube.com/channel/{channel_id}/videos"
        
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
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
                
                logger.info(f"Found {len(videos)} videos from channel {channel_id}")
                return videos
                
            except Exception as e:
                logger.error(f"Error fetching channel videos: {e}")
                return []
    
    def get_recent_episodes(self, channel_name: str = 'tetragrammaton', days_back: int = 30) -> List[Dict]:
        """Get recent episodes from specified channel."""
        channel_id = self.rick_rubin_channels.get(channel_name)
        if not channel_id:
            logger.error(f"Unknown channel: {channel_name}")
            return []
        
        videos = self.get_channel_videos(channel_id)
        
        # Filter by date if upload_date is available
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_videos = []
        
        for video in videos:
            if video.get('upload_date'):
                try:
                    upload_date = datetime.strptime(video['upload_date'], '%Y%m%d')
                    if upload_date >= cutoff_date:
                        recent_videos.append(video)
                except:
                    recent_videos.append(video)  # Include if date parsing fails
            else:
                recent_videos.append(video)  # Include if no date
        
        logger.info(f"Found {len(recent_videos)} videos from last {days_back} days")
        return recent_videos
    
    def collect_single(self, url: str) -> Optional[Dict]:
        """Collect transcript from a single YouTube video."""
        # Extract video ID from URL
        video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
        if not video_id_match:
            logger.error(f"Could not extract video ID from URL: {url}")
            return None
        
        video_id = video_id_match.group(1)
        
        try:
            # Get video info
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            # Get transcript
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            # Combine transcript segments
            full_text = ' '.join([segment['text'] for segment in transcript_list])
            
            # Clean up common issues
            full_text = re.sub(r'\s+', ' ', full_text)  # Multiple spaces
            full_text = re.sub(r'\[.*?\]', '', full_text)  # Remove [Music] etc
            
            result = {
                'video_id': video_id,
                'url': url,
                'title': info.get('title', ''),
                'channel': info.get('channel', ''),
                'upload_date': info.get('upload_date', ''),
                'duration': info.get('duration', 0),
                'transcript': full_text,
                'word_count': len(full_text.split()),
                'collected_at': datetime.now().isoformat(),
            }
            
            logger.info(f"Collected transcript from: {result['title']} ({result['word_count']} words)")
            return result
            
        except Exception as e:
            logger.error(f"Error collecting transcript from {url}: {e}")
            return None
    
    def collect_batch(self, urls: List[str]) -> List[Dict]:
        """Collect transcripts from multiple URLs."""
        results = []
        for i, url in enumerate(urls):
            logger.info(f"Processing {i+1}/{len(urls)}: {url}")
            result = self.collect_single(url)
            if result:
                results.append(result)
        
        logger.info(f"Successfully collected {len(results)}/{len(urls)} transcripts")
        return results
    
    def search_rick_rubin_content(self, query: str = "Rick Rubin", max_results: int = 50) -> List[Dict]:
        """Search YouTube for Rick Rubin content."""
        search_opts = {
            **self.ydl_opts,
            'default_search': 'ytsearch',
            'max_downloads': max_results,
        }
        
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
                entries = info.get('entries', [])
                
                videos = []
                for entry in entries:
                    if entry and self._is_relevant_content(entry):
                        videos.append({
                            'video_id': entry.get('id'),
                            'title': entry.get('title'),
                            'url': f"https://youtube.com/watch?v={entry.get('id')}",
                            'channel': entry.get('channel'),
                            'duration': entry.get('duration'),
                        })
                
                logger.info(f"Found {len(videos)} relevant videos for query: {query}")
                return videos
                
            except Exception as e:
                logger.error(f"Error searching YouTube: {e}")
                return []
    
    def _is_relevant_content(self, video_info: Dict) -> bool:
        """Check if video is likely to contain valuable Rick Rubin content."""
        title = video_info.get('title', '').lower()
        channel = video_info.get('channel', '').lower()
        duration = video_info.get('duration', 0)
        
        # Skip short clips (less than 5 minutes)
        if duration and duration < 300:
            return False
        
        # Check for Rick Rubin mentions
        rick_indicators = ['rick rubin', 'rubin', 'tetragrammaton']
        if not any(indicator in title or indicator in channel for indicator in rick_indicators):
            return False
        
        # Skip compilations and reaction videos
        skip_terms = ['reaction', 'reacts', 'compilation', 'best of', 'top 10']
        if any(term in title for term in skip_terms):
            return False
        
        return True


def main():
    """Example usage of YouTube collector."""
    collector = YouTubeCollector()
    
    # Example: Get recent Tetragrammaton episodes
    print("\n=== Recent Tetragrammaton Episodes ===")
    recent = collector.get_recent_episodes('tetragrammaton', days_back=60)
    for video in recent[:5]:
        print(f"- {video['title']}")
        print(f"  URL: {video['url']}")
        print(f"  Date: {video.get('upload_date', 'Unknown')}")
        print()
    
    # Example: Collect single video
    if recent:
        print("\n=== Collecting First Episode ===")
        result = collector.collect_single(recent[0]['url'])
        if result:
            print(f"Title: {result['title']}")
            print(f"Words: {result['word_count']}")
            print(f"Sample: {result['transcript'][:200]}...")


if __name__ == "__main__":
    main()
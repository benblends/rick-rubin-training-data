#!/usr/bin/env python3
"""Manual fallback collector for when automated methods fail"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

class ManualFallbackCollector:
    """Collect transcripts manually when automation fails."""
    
    def __init__(self, data_dir: str = "data/manual_transcripts"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # High-value Rick Rubin content that we know exists
        self.high_priority_content = [
            {
                'video_id': 'qkwISstQQVw',
                'title': 'The Rick Rubin Interview - Rick Beato',
                'channel': 'Rick Beato',
                'description': 'Deep conversation about production philosophy',
                'priority': 10,
            },
            {
                'video_id': '4lPD5PtqMiE',
                'title': 'Kendrick Lamar & Rick Rubin Have an Epic Conversation',
                'channel': 'GQ',
                'description': 'Discussion about creativity and hip-hop production',
                'priority': 9,
            },
            {
                'video_id': 'H_oznVVaflg',
                'title': 'Rick Rubin - On Being with Krista Tippett',
                'channel': 'On Being',
                'description': 'Philosophical discussion about creativity',
                'priority': 10,
            },
            {
                'video_id': 'GtaxU6fd7sI',
                'title': 'Jack Black - Tetragrammaton with Rick Rubin',
                'channel': 'Tetragrammaton',
                'description': 'Recent episode from Rick\'s own podcast',
                'priority': 8,
            }
        ]
    
    def add_manual_transcript(self, video_id: str, title: str, channel: str, 
                            transcript_text: str, metadata: Optional[Dict] = None) -> Dict:
        """Add a manually obtained transcript."""
        
        entry = {
            'video_id': video_id,
            'title': title,
            'channel': channel,
            'transcript': transcript_text,
            'word_count': len(transcript_text.split()),
            'collection_method': 'manual',
            'collected_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        # Save to file
        filename = self.data_dir / f"{video_id}_manual.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved manual transcript: {title}")
        print(f"  Location: {filename}")
        print(f"  Words: {entry['word_count']}")
        
        return entry
    
    def add_placeholder(self, video_id: str, title: str, channel: str, 
                       reason: str = "Automated collection failed") -> Dict:
        """Add a placeholder for content to be collected later."""
        
        entry = {
            'video_id': video_id,
            'title': title,
            'channel': channel,
            'status': 'pending_collection',
            'reason': reason,
            'created_at': datetime.now().isoformat(),
        }
        
        # Save to tracking file
        tracking_file = self.data_dir / "pending_collection.json"
        
        # Load existing entries
        if tracking_file.exists():
            with open(tracking_file, 'r') as f:
                pending = json.load(f)
        else:
            pending = []
        
        # Add new entry if not already present
        if not any(p['video_id'] == video_id for p in pending):
            pending.append(entry)
            
            with open(tracking_file, 'w') as f:
                json.dump(pending, f, indent=2)
            
            print(f"📋 Added to pending collection: {title}")
        
        return entry
    
    def get_sample_transcript(self) -> str:
        """Return a sample Rick Rubin transcript for testing."""
        
        # This is a fabricated example in Rick Rubin's style
        sample = """
        The thing about production is that it's not about adding more. It's about finding 
        what's already there and revealing it. When I worked with Johnny Cash on the American 
        Recordings, we stripped everything away. Just him and his guitar. That's when you 
        could really hear the soul of the song.
        
        I think the role of a producer is to be a mirror for the artist. To help them see 
        what they might not see themselves. Sometimes that means saying less. Sometimes it 
        means creating a space where they feel safe to be vulnerable.
        
        The best albums often come from a place of not knowing. When you think you know 
        exactly what you're doing, that's when you're in trouble. The magic happens in the 
        uncertainty, in the exploration. That's where the real discoveries are made.
        
        With the Red Hot Chili Peppers on Blood Sugar Sex Magik, we went to this mansion 
        and just lived there. We weren't making a record, we were living a life that 
        happened to include making music. That's a very different energy than going to a 
        studio from 2 to 6.
        
        I don't believe in the idea of fixing things in the mix. If it doesn't feel right 
        when you're recording it, it's not going to feel right later. The emotion has to 
        be there in the moment. You can't manufacture that afterwards.
        """
        
        return sample.strip()
    
    def list_pending(self) -> list:
        """List all pending collections."""
        tracking_file = self.data_dir / "pending_collection.json"
        
        if tracking_file.exists():
            with open(tracking_file, 'r') as f:
                return json.load(f)
        return []
    
    def create_collection_instructions(self) -> str:
        """Generate instructions for manual collection."""
        
        instructions = """
# Manual Transcript Collection Instructions

Since automated collection is currently failing, here are methods for manual collection:

## Method 1: YouTube Transcript Copy
1. Go to the YouTube video
2. Click the "..." menu below the video
3. Select "Show transcript"
4. Click the three dots in the transcript window
5. Toggle off timestamps
6. Select all text and copy

## Method 2: Browser Extensions
- "YouTube Transcript Extractor" Chrome extension
- "Transcripts for YouTube" Firefox addon

## Method 3: Alternative Services
- downsub.com (paste YouTube URL)
- youtubetranscript.com
- Rev.com (paid service, high quality)

## High Priority Videos to Collect:
"""
        
        for content in sorted(self.high_priority_content, key=lambda x: x['priority'], reverse=True):
            instructions += f"\n### {content['title']}"
            instructions += f"\n- URL: https://youtube.com/watch?v={content['video_id']}"
            instructions += f"\n- Channel: {content['channel']}"
            instructions += f"\n- Priority: {content['priority']}/10"
            instructions += f"\n- Description: {content['description']}\n"
        
        instructions += """
## Storage Format
Save transcripts as text files named: `{video_id}_transcript.txt`
Place in: `data/manual_transcripts/`

## Quality Guidelines
- Prefer videos where Rick Rubin is the main speaker
- Look for discussions about production philosophy
- Prioritize recent content (Tetragrammaton podcast)
- Include conversations about specific albums/artists
"""
        
        return instructions


def main():
    """Demonstrate manual fallback collector."""
    collector = ManualFallbackCollector()
    
    print("=== Manual Fallback Collector ===\n")
    
    # Add placeholders for high-priority content
    print("Adding placeholders for high-priority content...\n")
    for content in collector.high_priority_content[:3]:
        collector.add_placeholder(
            video_id=content['video_id'],
            title=content['title'],
            channel=content['channel'],
            reason="YouTube API errors - manual collection needed"
        )
    
    # Demonstrate adding a sample transcript
    print("\n\nAdding sample transcript for testing...")
    sample_text = collector.get_sample_transcript()
    collector.add_manual_transcript(
        video_id="sample_001",
        title="Sample Rick Rubin Philosophy",
        channel="Test Channel",
        transcript_text=sample_text,
        metadata={'source': 'fabricated_example', 'purpose': 'testing'}
    )
    
    # Generate instructions
    print("\n\nGenerating collection instructions...")
    instructions_file = Path("data/manual_transcripts/COLLECTION_INSTRUCTIONS.md")
    instructions_file.parent.mkdir(parents=True, exist_ok=True)
    instructions_file.write_text(collector.create_collection_instructions())
    print(f"Instructions saved to: {instructions_file}")
    
    # List pending
    print("\n\nPending collections:")
    for item in collector.list_pending():
        print(f"- {item['title']} ({item['video_id']})")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Quick test of collection pipeline with single Rick Rubin video."""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.youtube_collector import YouTubeCollector
from processors.transcript_cleaner import TranscriptCleaner


def test_single_video(url: str = None):
    """Test collection and cleaning pipeline with a single video."""
    
    # Default to a known good Rick Rubin interview if no URL provided
    if not url:
        # On Being interview with Krista Tippett (high quality philosophical content)
        url = "https://www.youtube.com/watch?v=H_uznVVaflg"
        print(f"No URL provided, using default: {url}")
    
    print("\n=== YouTube Collector Test ===")
    collector = YouTubeCollector()
    
    # Collect transcript
    print(f"Collecting transcript from: {url}")
    raw_data = collector.collect_single(url)
    
    if not raw_data:
        print("ERROR: Failed to collect transcript")
        return False
    
    print(f"\nSuccess! Collected transcript:")
    print(f"- Title: {raw_data['title']}")
    print(f"- Channel: {raw_data['channel']}")
    print(f"- Duration: {raw_data['duration']} seconds")
    print(f"- Raw word count: {raw_data['word_count']}")
    print(f"\nSample (first 200 chars):")
    print(raw_data['transcript'][:200] + "...")
    
    # Clean transcript
    print("\n\n=== Transcript Cleaner Test ===")
    cleaner = TranscriptCleaner()
    cleaned_data = cleaner.process(raw_data)
    
    print(f"\nCleaning complete:")
    print(f"- Cleaned word count: {cleaned_data['cleaned_word_count']}")
    print(f"- Number of segments: {len(cleaned_data['segments'])}")
    print(f"\nQuality metrics:")
    for key, value in cleaned_data['quality_metrics'].items():
        print(f"  - {key}: {value}")
    
    print(f"\nCleaned sample (first 200 chars):")
    print(cleaned_data['cleaned_text'][:200] + "...")
    
    # Save test output
    output_dir = Path("data/test_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save raw data
    raw_file = output_dir / f"raw_{raw_data['video_id']}.json"
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, indent=2, ensure_ascii=False)
    print(f"\nRaw data saved to: {raw_file}")
    
    # Save cleaned data
    cleaned_file = output_dir / f"cleaned_{raw_data['video_id']}.json"
    with open(cleaned_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    print(f"Cleaned data saved to: {cleaned_file}")
    
    # Save segments as text file for easy reading
    segments_file = output_dir / f"segments_{raw_data['video_id']}.txt"
    with open(segments_file, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(cleaned_data['segments']):
            f.write(f"=== SEGMENT {i+1} ===\n")
            f.write(f"Words: {len(segment.split())}\n\n")
            f.write(segment)
            f.write("\n\n" + "="*50 + "\n\n")
    print(f"Segments saved to: {segments_file}")
    
    return True


def test_recent_episodes():
    """Test fetching recent Tetragrammaton episodes."""
    print("\n=== Testing Recent Episodes Fetch ===")
    collector = YouTubeCollector()
    
    recent = collector.get_recent_episodes('tetragrammaton', days_back=30)
    
    if not recent:
        print("No recent episodes found")
        return False
    
    print(f"\nFound {len(recent)} recent episodes:")
    for i, video in enumerate(recent[:5]):  # Show first 5
        print(f"\n{i+1}. {video['title']}")
        print(f"   URL: {video['url']}")
        print(f"   Date: {video.get('upload_date', 'Unknown')}")
    
    # Test collecting the first one
    if recent:
        print(f"\n\nTesting collection of most recent episode...")
        return test_single_video(recent[0]['url'])
    
    return True


def test_search():
    """Test searching for Rick Rubin content."""
    print("\n=== Testing YouTube Search ===")
    collector = YouTubeCollector()
    
    results = collector.search_rick_rubin_content("Rick Rubin interview", max_results=10)
    
    if not results:
        print("No search results found")
        return False
    
    print(f"\nFound {len(results)} videos:")
    for i, video in enumerate(results[:5]):  # Show first 5
        print(f"\n{i+1}. {video['title']}")
        print(f"   Channel: {video['channel']}")
        print(f"   URL: {video['url']}")
    
    return True


def main():
    """Run all tests."""
    print("Rick Rubin Training Data Collection - Quick Test")
    print("=" * 50)
    
    # Check if user provided a URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"Testing with provided URL: {url}")
        success = test_single_video(url)
    else:
        # Run default tests
        print("Running default test suite...\n")
        
        # Test 1: Single video with known good URL
        print("TEST 1: Single Video Collection")
        test1 = test_single_video()
        
        # Test 2: Recent episodes
        print("\n\nTEST 2: Recent Episodes")
        test2 = test_recent_episodes()
        
        # Test 3: Search functionality
        print("\n\nTEST 3: Search Functionality")
        test3 = test_search()
        
        # Summary
        print("\n\n=== TEST SUMMARY ===")
        print(f"Single video test: {'PASSED' if test1 else 'FAILED'}")
        print(f"Recent episodes test: {'PASSED' if test2 else 'FAILED'}")
        print(f"Search test: {'PASSED' if test3 else 'FAILED'}")
        
        success = all([test1, test2, test3])
    
    if success:
        print("\n✅ All tests passed! The collection pipeline is working.")
        print("\nNext steps:")
        print("1. Check the data/test_outputs directory for collected data")
        print("2. Review quality scores to set appropriate thresholds")
        print("3. Run larger batch collections with:")
        print("   python collectors/youtube_collector.py")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
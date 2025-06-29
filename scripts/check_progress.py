#!/usr/bin/env python3
"""Quick progress check for Rick Rubin data collection."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.progress_tracker import ProgressTracker


def main():
    """Display current progress report."""
    tracker = ProgressTracker()
    print(tracker.generate_report())
    
    # Also show pending processing
    print("\n📋 PENDING PROCESSING:")
    
    pending_clean = tracker.get_pending_processing('cleaned')
    if pending_clean:
        print(f"\nAwaiting cleaning: {len(pending_clean)} files")
        for item in pending_clean[:5]:
            print(f"  - {item['source_name']}")
        if len(pending_clean) > 5:
            print(f"  ... and {len(pending_clean) - 5} more")
    
    pending_format = tracker.get_pending_processing('formatted')
    if pending_format:
        print(f"\nAwaiting formatting: {len(pending_format)} files")
        for item in pending_format[:5]:
            print(f"  - {item['source_name']}")
        if len(pending_format) > 5:
            print(f"  ... and {len(pending_format) - 5} more")
    
    # Show high quality sources
    high_quality = tracker.get_high_quality_sources(min_score=85.0)
    if high_quality:
        print(f"\n⭐ HIGH QUALITY SOURCES (85+):")
        for source in high_quality[:5]:
            print(f"  - {source['source_name']} (score: {source['quality_score']:.1f})")
        if len(high_quality) > 5:
            print(f"  ... and {len(high_quality) - 5} more")
    
    print("\n" + "="*60)
    print("Use 'python scripts/batch_processor.py' to process pending files")
    print("Use 'python scripts/export_for_ollama.py' to create training set")


if __name__ == "__main__":
    main()
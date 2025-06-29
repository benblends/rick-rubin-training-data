# Rick Rubin Training Data Collection System

Automated collection system for gathering Rick Rubin training data for Ollama fine-tuning.

## Overview

This project implements an automated pipeline for collecting, processing, and formatting Rick Rubin's production wisdom, interviews, and creative philosophy for training a custom AI model.

## Quick Start

```bash
# Setup
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Test with single video
python scripts/quick_test.py

# Run collection
python collectors/youtube_collector.py --channel tetragrammaton --limit 5
```

## Project Structure

```
rick-rubin-training-data/
├── collectors/          # Data collection modules
│   └── youtube_collector.py
├── processors/          # Text processing and cleaning
│   └── transcript_cleaner.py
├── scripts/            # Utility scripts
│   └── quick_test.py
└── data/              # Collected data (gitignored)
```

## MVP Features (Day 1)

- YouTube transcript collection from Tetragrammaton podcast
- Basic text cleaning and processing
- Quick testing script for single video validation

## Roadmap

- [ ] Podcast transcription with Whisper
- [ ] Web article scraping
- [ ] Music database integration
- [ ] Quality scoring and validation
- [ ] Ollama training format export

## Data Sources

### High Priority
- **Tetragrammaton Podcast** - Rick Rubin's own podcast
- **On Being Interview** - Deep philosophical discussion
- **The Creative Act** - Book excerpts (manual entry)

### Medium Priority
- Production credits from AllMusic/Discogs
- Music journalism articles
- Other podcast appearances

## License

This project is for educational and research purposes. All collected content remains property of original creators.
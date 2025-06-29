#!/usr/bin/env python3
"""Clean and process transcripts for training data preparation."""

import re
import unicodedata
from typing import Dict, List, Optional, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranscriptCleaner:
    """Clean and normalize transcript text for training."""
    
    def __init__(self):
        # Common filler words in transcripts
        self.filler_words = {
            'um', 'uh', 'uhm', 'ah', 'eh', 'hmm', 'mm-hmm', 
            'uh-huh', 'mm-mm', 'mhm'
        }
        
        # Rick Rubin indicators for quality scoring
        self.rick_indicators = [
            "i think", "i believe", "in my experience",
            "when i produced", "the way i see it", "i've found",
            "i feel", "i've learned", "i remember"
        ]
        
        # Production and philosophy terms
        self.quality_terms = [
            "production", "mixing", "arrangement", "frequency", 
            "emotion", "creative", "artist", "song", "music",
            "studio", "recording", "album", "sound", "feeling",
            "essence", "stripped down", "less is more", "simplicity"
        ]
    
    def process(self, transcript_data: Dict) -> Dict:
        """Process a single transcript."""
        if isinstance(transcript_data, str):
            # Handle plain text input
            text = transcript_data
            metadata = {}
        else:
            # Handle dictionary input
            text = transcript_data.get('transcript', '')
            metadata = {k: v for k, v in transcript_data.items() if k != 'transcript'}
        
        # Apply cleaning pipeline
        cleaned_text = self.clean_text(text)
        
        # Calculate quality metrics
        quality_metrics = self.calculate_quality_metrics(cleaned_text)
        
        # Split into segments for better training
        segments = self.segment_text(cleaned_text)
        
        result = {
            **metadata,
            'cleaned_text': cleaned_text,
            'segments': segments,
            'quality_metrics': quality_metrics,
            'cleaned_word_count': len(cleaned_text.split()),
        }
        
        return result
    
    def clean_text(self, text: str) -> str:
        """Apply comprehensive text cleaning."""
        if not text:
            return ""
        
        # Normalize unicode
        text = unicodedata.normalize('NFKD', text)
        
        # Convert to lowercase for processing
        text_lower = text.lower()
        
        # Remove timestamps like [00:00:00]
        text = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', text)
        text = re.sub(r'\[\d{2}:\d{2}\]', '', text)
        
        # Remove speaker labels like "Rick:" or "RICK RUBIN:"
        text = re.sub(r'^[A-Z][A-Za-z\s]+:', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n[A-Z][A-Za-z\s]+:', ' ', text)
        
        # Remove sound effects and annotations
        text = re.sub(r'\[.*?\]', '', text)  # [Music], [Laughter], etc.
        text = re.sub(r'\(.*?\)', '', text)  # (unintelligible), etc.
        
        # Clean up filler words (preserve case)
        for filler in self.filler_words:
            # Word boundary replacement
            text = re.sub(rf'\b{filler}\b', '', text, flags=re.IGNORECASE)
        
        # Fix transcript artifacts
        text = re.sub(r'\.{3,}', '...', text)  # Multiple periods
        text = re.sub(r'-{2,}', '--', text)    # Multiple dashes
        text = re.sub(r'\s+', ' ', text)       # Multiple spaces
        text = re.sub(r'\n{3,}', '\n\n', text) # Multiple newlines
        
        # Fix common transcription errors
        text = text.replace(' gonna ', ' going to ')
        text = text.replace(' wanna ', ' want to ')
        text = text.replace(' gotta ', ' got to ')
        text = text.replace(' kinda ', ' kind of ')
        text = text.replace(' sorta ', ' sort of ')
        
        # Clean up punctuation spacing
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)  # Space before punctuation
        text = re.sub(r'([.,!?;:])\s*', r'\1 ', text) # Ensure space after
        
        # Trim whitespace
        text = text.strip()
        
        return text
    
    def segment_text(self, text: str, target_length: int = 500) -> List[str]:
        """Split text into meaningful segments for training."""
        if not text:
            return []
        
        # First try to split by paragraphs
        paragraphs = text.split('\n\n')
        
        segments = []
        current_segment = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If paragraph is short enough, check if we can combine with current
            if len(para.split()) < target_length:
                if len(current_segment.split()) + len(para.split()) < target_length * 1.5:
                    current_segment += "\n\n" + para if current_segment else para
                else:
                    if current_segment:
                        segments.append(current_segment.strip())
                    current_segment = para
            else:
                # Paragraph too long, need to split by sentences
                if current_segment:
                    segments.append(current_segment.strip())
                    current_segment = ""
                
                sentences = self._split_sentences(para)
                for sentence in sentences:
                    if len(current_segment.split()) + len(sentence.split()) < target_length:
                        current_segment += " " + sentence if current_segment else sentence
                    else:
                        if current_segment:
                            segments.append(current_segment.strip())
                        current_segment = sentence
        
        # Don't forget the last segment
        if current_segment:
            segments.append(current_segment.strip())
        
        # Filter out very short segments
        segments = [s for s in segments if len(s.split()) > 50]
        
        return segments
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitter (can be improved)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def calculate_quality_metrics(self, text: str) -> Dict[str, float]:
        """Calculate quality metrics for the text."""
        if not text:
            return {'overall_score': 0, 'rick_score': 0, 'production_score': 0}
        
        text_lower = text.lower()
        word_count = len(text.split())
        
        # Calculate Rick Rubin authenticity score
        rick_score = 0
        for indicator in self.rick_indicators:
            rick_score += text_lower.count(indicator) * 10
        
        # Calculate production/music relevance score
        production_score = 0
        for term in self.quality_terms:
            production_score += text_lower.count(term) * 5
        
        # Normalize scores
        rick_score = min(100, rick_score * 100 / max(word_count, 1))
        production_score = min(100, production_score * 100 / max(word_count, 1))
        
        # Check for specific album/artist mentions (high value)
        album_mentions = len(re.findall(r'\b(album|record|produced|production)\b', text_lower))
        artist_mentions = len(re.findall(r'\b(johnny cash|red hot chili peppers|beastie boys|jay-z|kanye|metallica|slayer)\b', text_lower))
        
        # Calculate overall score
        overall_score = (
            rick_score * 0.4 +
            production_score * 0.3 +
            min(100, album_mentions * 10) * 0.2 +
            min(100, artist_mentions * 15) * 0.1
        )
        
        return {
            'overall_score': round(overall_score, 2),
            'rick_score': round(rick_score, 2),
            'production_score': round(production_score, 2),
            'album_mentions': album_mentions,
            'artist_mentions': artist_mentions,
        }
    
    def is_high_quality(self, text: str, threshold: float = 70.0) -> bool:
        """Quick check if text meets quality threshold."""
        metrics = self.calculate_quality_metrics(text)
        return metrics['overall_score'] >= threshold


def main():
    """Example usage of transcript cleaner."""
    cleaner = TranscriptCleaner()
    
    # Example transcript snippet
    sample = """
    [00:00:15] INTERVIEWER: So, Rick, tell us about your approach to production.
    
    RICK RUBIN: Well, um, I think the most important thing is to, uh, really listen to what the artist 
    is trying to say. [Music] When I produced Johnny Cash's album, we kinda stripped everything down 
    to its essence. It's about finding the emotional core of the song, you know?
    
    I've learned that less is more... The best productions often have the least in them. 
    It's not about adding layers - it's about revealing what's already there.
    """
    
    # Process the sample
    result = cleaner.process(sample)
    
    print("=== Original ===")
    print(f"Words: {len(sample.split())}")
    print(sample[:200] + "...")
    
    print("\n=== Cleaned ===")
    print(f"Words: {result['cleaned_word_count']}")
    print(result['cleaned_text'][:200] + "...")
    
    print("\n=== Quality Metrics ===")
    for key, value in result['quality_metrics'].items():
        print(f"{key}: {value}")
    
    print(f"\n=== Segments ({len(result['segments'])}) ===")
    for i, segment in enumerate(result['segments'][:2]):
        print(f"\nSegment {i+1}:")
        print(segment[:150] + "...")


if __name__ == "__main__":
    main()
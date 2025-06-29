#!/usr/bin/env python3
"""Format cleaned transcripts for Ollama training."""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrainingFormatter:
    """Format transcripts into Ollama training format."""
    
    def __init__(self):
        # Varied instruction templates to avoid overfitting
        self.instruction_templates = {
            'philosophy': [
                "Share your thoughts on this topic:",
                "What's your perspective on this?",
                "Explain your philosophy about this:",
                "How do you think about this subject?",
                "Describe your approach to this:",
                "What have you learned about this?",
                "Share your wisdom on this topic:",
            ],
            'production': [
                "Describe your production approach for this:",
                "How would you produce this?",
                "Explain the production decisions here:",
                "Share your production philosophy on this:",
                "What's your approach to producing this?",
                "How do you handle this in the studio?",
                "Describe the creative process for this:",
            ],
            'artist_story': [
                "Tell the story about working with this artist:",
                "Share your experience producing this:",
                "Describe what happened when you worked on this:",
                "Tell us about this production:",
                "Share the creative journey of this project:",
                "What was it like working on this?",
                "Describe the collaboration on this:",
            ],
            'advice': [
                "What advice would you give about this?",
                "How would you guide someone on this?",
                "What would you tell an artist about this?",
                "Share your guidance on this topic:",
                "What wisdom can you offer about this?",
                "How would you coach someone on this?",
                "What would you say to someone facing this?",
            ],
            'general': [
                "Share your thoughts:",
                "Tell us more about this:",
                "Explain this concept:",
                "Describe your perspective:",
                "What can you tell us about this?",
                "Share your insights:",
                "Elaborate on this topic:",
            ]
        }
        
        # Context extractors for different content types
        self.context_markers = {
            'album_discussion': ['album', 'record', 'produced', 'recorded'],
            'artist_mention': ['johnny cash', 'red hot chili peppers', 'beastie boys', 
                              'metallica', 'slayer', 'kanye', 'jay-z', 'kendrick'],
            'philosophy': ['believe', 'think', 'feel', 'approach', 'philosophy'],
            'technique': ['studio', 'mixing', 'recording', 'sound', 'frequency'],
        }
    
    def format_for_ollama(self, cleaned_data: Dict, min_quality: float = 50.0) -> List[Dict]:
        """Format cleaned transcript data for Ollama training."""
        
        # Check quality threshold
        quality_score = cleaned_data.get('quality_metrics', {}).get('overall_score', 0)
        if quality_score < min_quality:
            logger.warning(f"Skipping low quality content (score: {quality_score})")
            return []
        
        # Get segments or create from full text
        segments = cleaned_data.get('segments', [])
        if not segments and 'cleaned_text' in cleaned_data:
            segments = [cleaned_data['cleaned_text']]
        
        training_examples = []
        
        for segment in segments:
            if len(segment.split()) < 50:  # Skip very short segments
                continue
            
            # Determine content type
            content_type = self._determine_content_type(segment)
            
            # Create multiple training examples from the segment
            examples = self._create_training_examples(segment, content_type, cleaned_data)
            training_examples.extend(examples)
        
        logger.info(f"Created {len(training_examples)} training examples from {len(segments)} segments")
        return training_examples
    
    def _determine_content_type(self, text: str) -> str:
        """Determine the type of content for appropriate formatting."""
        text_lower = text.lower()
        
        # Check for specific patterns
        if any(artist in text_lower for artist in self.context_markers['artist_mention']):
            if any(word in text_lower for word in ['worked', 'produced', 'recorded']):
                return 'artist_story'
            return 'production'
        
        if sum(word in text_lower for word in self.context_markers['philosophy']) >= 2:
            return 'philosophy'
        
        if sum(word in text_lower for word in self.context_markers['technique']) >= 2:
            return 'production'
        
        if any(phrase in text_lower for phrase in ['would you', 'how to', 'advice', 'suggest']):
            return 'advice'
        
        return 'general'
    
    def _create_training_examples(self, segment: str, content_type: str, 
                                metadata: Dict) -> List[Dict]:
        """Create training examples from a segment."""
        examples = []
        
        # Split long segments into smaller chunks with context
        chunks = self._split_with_context(segment, max_words=300, overlap=50)
        
        for i, chunk in enumerate(chunks):
            # Skip if too short
            if len(chunk.split()) < 50:
                continue
            
            # Extract context and response
            context, response = self._extract_context_response(chunk)
            
            # Select appropriate instruction
            instruction = random.choice(self.instruction_templates.get(content_type, 
                                                                     self.instruction_templates['general']))
            
            # Create training example
            example = {
                'instruction': instruction,
                'input': context,
                'output': response,
                'metadata': {
                    'source': metadata.get('title', 'Unknown'),
                    'video_id': metadata.get('video_id', ''),
                    'content_type': content_type,
                    'quality_score': metadata.get('quality_metrics', {}).get('overall_score', 0),
                    'segment_index': i,
                    'timestamp': datetime.now().isoformat(),
                }
            }
            
            examples.append(example)
        
        # Create additional Q&A style examples for high-quality content
        if metadata.get('quality_metrics', {}).get('overall_score', 0) > 70:
            qa_examples = self._create_qa_examples(segment, content_type, metadata)
            examples.extend(qa_examples)
        
        return examples
    
    def _split_with_context(self, text: str, max_words: int = 300, 
                          overlap: int = 50) -> List[str]:
        """Split text into chunks with overlapping context."""
        words = text.split()
        chunks = []
        
        if len(words) <= max_words:
            return [text]
        
        start = 0
        while start < len(words):
            end = min(start + max_words, len(words))
            chunk = ' '.join(words[start:end])
            chunks.append(chunk)
            
            # Move forward with overlap
            start = end - overlap if end < len(words) else end
        
        return chunks
    
    def _extract_context_response(self, text: str) -> Tuple[str, str]:
        """Extract context and response from text."""
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        if len(sentences) < 3:
            # Too short for context extraction
            return "", text
        
        # Use first 1-2 sentences as context
        context_sentences = 1 if len(sentences) < 5 else 2
        context = '. '.join(sentences[:context_sentences]) + '.'
        response = '. '.join(sentences[context_sentences:]) + '.'
        
        return context, response
    
    def _create_qa_examples(self, segment: str, content_type: str, 
                          metadata: Dict) -> List[Dict]:
        """Create question-answer style training examples."""
        examples = []
        
        # Generate questions based on content
        if content_type == 'artist_story':
            # Extract artist name if mentioned
            text_lower = segment.lower()
            for artist in self.context_markers['artist_mention']:
                if artist in text_lower:
                    question = f"Tell me about working with {artist.title()}"
                    examples.append({
                        'instruction': question,
                        'input': "",
                        'output': segment,
                        'metadata': {
                            **metadata.get('metadata', {}),
                            'format': 'qa',
                            'extracted_topic': artist,
                        }
                    })
                    break
        
        elif content_type == 'philosophy':
            # Create philosophy-focused questions
            if 'less is more' in segment.lower():
                examples.append({
                    'instruction': "Explain your 'less is more' philosophy",
                    'input': "",
                    'output': segment,
                    'metadata': {**metadata.get('metadata', {}), 'format': 'qa'}
                })
        
        elif content_type == 'production':
            # Create production-focused questions
            if 'studio' in segment.lower() or 'recording' in segment.lower():
                examples.append({
                    'instruction': "Describe your approach to studio recording",
                    'input': "",
                    'output': segment,
                    'metadata': {**metadata.get('metadata', {}), 'format': 'qa'}
                })
        
        return examples
    
    def export_to_jsonl(self, training_examples: List[Dict], 
                       output_path: str, quality_threshold: float = 0.0) -> str:
        """Export training examples to JSONL format for Ollama."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Filter by quality if threshold is set
        if quality_threshold > 0:
            training_examples = [
                ex for ex in training_examples 
                if ex.get('metadata', {}).get('quality_score', 0) >= quality_threshold
            ]
        
        # Write JSONL file
        with open(output_file, 'w', encoding='utf-8') as f:
            for example in training_examples:
                # Format for Ollama fine-tuning
                formatted = {
                    'instruction': example['instruction'],
                    'input': example['input'],
                    'output': example['output']
                }
                f.write(json.dumps(formatted, ensure_ascii=False) + '\n')
        
        logger.info(f"Exported {len(training_examples)} examples to {output_file}")
        return str(output_file)
    
    def create_validation_set(self, training_examples: List[Dict], 
                            validation_ratio: float = 0.1) -> Tuple[List[Dict], List[Dict]]:
        """Split examples into training and validation sets."""
        # Shuffle examples
        examples = training_examples.copy()
        random.shuffle(examples)
        
        # Calculate split
        val_size = int(len(examples) * validation_ratio)
        
        validation = examples[:val_size]
        training = examples[val_size:]
        
        logger.info(f"Split data: {len(training)} training, {len(validation)} validation")
        return training, validation


def main():
    """Test the training formatter."""
    formatter = TrainingFormatter()
    
    # Load sample cleaned data
    sample_file = Path("data/manual_transcripts/sample_001_cleaned.json")
    if sample_file.exists():
        with open(sample_file, 'r') as f:
            cleaned_data = json.load(f)
        
        print("=== Training Formatter Test ===")
        print(f"Input: {cleaned_data.get('title', 'Unknown')}")
        print(f"Quality Score: {cleaned_data.get('quality_metrics', {}).get('overall_score', 0)}")
        
        # Format for training
        examples = formatter.format_for_ollama(cleaned_data, min_quality=0)  # Accept all for testing
        
        print(f"\nGenerated {len(examples)} training examples")
        
        if examples:
            print("\n=== Sample Training Example ===")
            example = examples[0]
            print(f"Instruction: {example['instruction']}")
            print(f"Input: {example['input'][:100]}..." if example['input'] else "Input: (empty)")
            print(f"Output: {example['output'][:150]}...")
            print(f"Content Type: {example['metadata']['content_type']}")
            
            # Export to JSONL
            output_path = "data/exports/sample_training.jsonl"
            formatter.export_to_jsonl(examples, output_path)
            print(f"\n✓ Exported to: {output_path}")
    else:
        print("No sample data found. Run test_cleaner.py first.")


if __name__ == "__main__":
    main()
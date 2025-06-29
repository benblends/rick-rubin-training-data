#!/usr/bin/env python3
"""Batch processing for Rick Rubin transcripts."""

import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import argparse
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.transcript_cleaner import TranscriptCleaner
from processors.training_formatter import TrainingFormatter
from scripts.progress_tracker import ProgressTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchProcessor:
    """Process multiple transcripts in batch."""
    
    def __init__(self, input_dir: str = "data/manual_transcripts",
                 output_dir: str = "data/processed",
                 min_quality: float = 0.0):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.min_quality = min_quality
        
        # Ensure output directories exist
        (self.output_dir / "cleaned").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "formatted").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "exports").mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.cleaner = TranscriptCleaner()
        self.formatter = TrainingFormatter()
        self.tracker = ProgressTracker()
        
        # Track processing stats
        self.stats = {
            'files_processed': 0,
            'files_skipped': 0,
            'total_words': 0,
            'total_examples': 0,
            'quality_scores': []
        }
    
    def discover_transcripts(self) -> List[Path]:
        """Discover all transcript files to process."""
        # Look for various file types
        patterns = ['*.txt', '*.json', '*.md']
        files = []
        
        for pattern in patterns:
            files.extend(self.input_dir.glob(pattern))
        
        # Exclude special files
        exclude = ['COLLECTION_INSTRUCTIONS.md', 'WEEK1_TARGETS.md', 'pending_collection.json']
        files = [f for f in files if f.name not in exclude]
        
        logger.info(f"Discovered {len(files)} transcript files")
        return sorted(files)
    
    def load_transcript(self, file_path: Path) -> Dict:
        """Load transcript from file."""
        if file_path.suffix == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure transcript field exists
                if 'transcript' not in data and 'text' in data:
                    data['transcript'] = data['text']
                return data
        else:
            # Plain text file
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                return {
                    'transcript': text,
                    'title': file_path.stem.replace('_', ' ').title(),
                    'source_file': file_path.name
                }
    
    def process_file(self, file_path: Path) -> Tuple[bool, Dict]:
        """Process a single transcript file."""
        logger.info(f"Processing: {file_path.name}")
        
        try:
            # Load transcript
            transcript_data = self.load_transcript(file_path)
            
            # Clean transcript
            cleaned_data = self.cleaner.process(transcript_data)
            
            # Check quality threshold
            quality_score = cleaned_data.get('quality_metrics', {}).get('overall_score', 0)
            if quality_score < self.min_quality:
                logger.warning(f"Skipping {file_path.name} - quality score {quality_score:.1f} below threshold")
                self.stats['files_skipped'] += 1
                return False, {}
            
            # Record in database
            source_id = self.tracker.record_collection(
                source_type=self._determine_source_type(file_path),
                source_name=cleaned_data.get('title', file_path.stem),
                file_path=str(file_path),
                word_count=cleaned_data.get('cleaned_word_count', 0),
                quality_score=quality_score
            )
            
            # Record quality metrics
            self.tracker.record_quality_metrics(source_id, cleaned_data['quality_metrics'])
            
            # Save cleaned data
            cleaned_file = self.output_dir / "cleaned" / f"{file_path.stem}_cleaned.json"
            with open(cleaned_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
            
            self.tracker.update_processing_status(source_id, 'cleaned')
            
            # Format for training
            training_examples = self.formatter.format_for_ollama(cleaned_data, self.min_quality)
            
            if training_examples:
                # Save formatted data
                formatted_file = self.output_dir / "formatted" / f"{file_path.stem}_formatted.json"
                with open(formatted_file, 'w', encoding='utf-8') as f:
                    json.dump(training_examples, f, indent=2, ensure_ascii=False)
                
                self.tracker.update_processing_status(source_id, 'formatted')
                
                # Update stats
                self.stats['total_examples'] += len(training_examples)
            
            # Update overall stats
            self.stats['files_processed'] += 1
            self.stats['total_words'] += cleaned_data.get('cleaned_word_count', 0)
            self.stats['quality_scores'].append(quality_score)
            
            return True, {
                'source_id': source_id,
                'quality_score': quality_score,
                'word_count': cleaned_data.get('cleaned_word_count', 0),
                'examples': len(training_examples)
            }
            
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            return False, {}
    
    def _determine_source_type(self, file_path: Path) -> str:
        """Determine source type from filename."""
        name_lower = file_path.stem.lower()
        
        if 'tetragrammaton' in name_lower:
            return 'tetragrammaton'
        elif 'onbeing' in name_lower or 'on_being' in name_lower:
            return 'on_being'
        elif 'creative_act' in name_lower or 'creativeact' in name_lower:
            return 'book'
        elif 'interview' in name_lower:
            return 'interview'
        elif 'podcast' in name_lower:
            return 'podcast'
        else:
            return 'manual'
    
    def consolidate_training_data(self) -> str:
        """Consolidate all formatted data into single JSONL file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.output_dir / "exports" / f"rick_rubin_training_{timestamp}.jsonl"
        
        all_examples = []
        
        # Load all formatted files
        for formatted_file in (self.output_dir / "formatted").glob("*_formatted.json"):
            with open(formatted_file, 'r', encoding='utf-8') as f:
                examples = json.load(f)
                all_examples.extend(examples)
        
        # Export to JSONL
        if all_examples:
            output_path = self.formatter.export_to_jsonl(all_examples, str(output_file))
            
            # Record export
            avg_quality = sum(self.stats['quality_scores']) / len(self.stats['quality_scores']) if self.stats['quality_scores'] else 0
            self.tracker.record_export(
                export_file=str(output_file),
                total_examples=len(all_examples),
                avg_quality=avg_quality,
                min_threshold=self.min_quality,
                sources_included=self.stats['files_processed']
            )
            
            logger.info(f"Exported {len(all_examples)} training examples to {output_file}")
            return str(output_file)
        else:
            logger.warning("No training examples to export")
            return ""
    
    def run(self, validate_only: bool = False) -> Dict:
        """Run batch processing on all discovered files."""
        files = self.discover_transcripts()
        
        if not files:
            logger.warning("No transcript files found")
            return self.stats
        
        # Process each file
        for file_path in files:
            if validate_only:
                # Just check if file can be loaded
                try:
                    self.load_transcript(file_path)
                    logger.info(f"✓ Valid: {file_path.name}")
                except Exception as e:
                    logger.error(f"✗ Invalid: {file_path.name} - {e}")
            else:
                success, result = self.process_file(file_path)
                if success:
                    logger.info(f"✓ Processed: {file_path.name} "
                              f"(quality: {result['quality_score']:.1f}, "
                              f"examples: {result['examples']})")
        
        if not validate_only and self.stats['files_processed'] > 0:
            # Consolidate and export
            export_file = self.consolidate_training_data()
            self.stats['export_file'] = export_file
        
        return self.stats
    
    def print_summary(self):
        """Print processing summary."""
        print("\n" + "="*60)
        print("BATCH PROCESSING SUMMARY")
        print("="*60)
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Files skipped: {self.stats['files_skipped']}")
        print(f"Total words: {self.stats['total_words']:,}")
        print(f"Training examples: {self.stats['total_examples']}")
        
        if self.stats['quality_scores']:
            avg_quality = sum(self.stats['quality_scores']) / len(self.stats['quality_scores'])
            print(f"Average quality: {avg_quality:.1f}")
            print(f"Quality range: {min(self.stats['quality_scores']):.1f} - {max(self.stats['quality_scores']):.1f}")
        
        if 'export_file' in self.stats:
            print(f"\nExported to: {self.stats['export_file']}")


def main():
    """Run batch processor from command line."""
    parser = argparse.ArgumentParser(description="Batch process Rick Rubin transcripts")
    parser.add_argument('--input-dir', default='data/manual_transcripts',
                       help='Input directory containing transcripts')
    parser.add_argument('--output-dir', default='data/processed',
                       help='Output directory for processed files')
    parser.add_argument('--min-quality', type=float, default=0.0,
                       help='Minimum quality score threshold')
    parser.add_argument('--validate', action='store_true',
                       help='Validate files only, do not process')
    
    args = parser.parse_args()
    
    # Create processor
    processor = BatchProcessor(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        min_quality=args.min_quality
    )
    
    # Run processing
    stats = processor.run(validate_only=args.validate)
    
    # Print summary
    processor.print_summary()
    
    # Generate progress report
    if not args.validate:
        print("\n" + processor.tracker.generate_report())


if __name__ == "__main__":
    main()
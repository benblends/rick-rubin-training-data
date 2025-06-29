#!/usr/bin/env python3
"""Export processed data for Ollama fine-tuning."""

import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import argparse
import logging
from datetime import datetime
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.progress_tracker import ProgressTracker
from processors.training_formatter import TrainingFormatter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OllamaExporter:
    """Export training data in Ollama format."""
    
    def __init__(self, min_quality: float = 80.0, validation_split: float = 0.1):
        self.min_quality = min_quality
        self.validation_split = validation_split
        self.tracker = ProgressTracker()
        self.formatter = TrainingFormatter()
        
        # Export directories
        self.export_dir = Path("data/exports")
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def load_all_training_data(self) -> List[Dict]:
        """Load all formatted training data."""
        all_examples = []
        
        # Check multiple possible locations
        search_dirs = [
            Path("data/processed/formatted"),
            Path("data/exports"),
        ]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
                
            # Load JSON files
            for json_file in search_dir.glob("*.json"):
                if 'formatted' in json_file.name or 'training' in json_file.name:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                all_examples.extend(data)
                            elif isinstance(data, dict) and 'examples' in data:
                                all_examples.extend(data['examples'])
                    except Exception as e:
                        logger.warning(f"Error loading {json_file}: {e}")
        
        logger.info(f"Loaded {len(all_examples)} total training examples")
        return all_examples
    
    def filter_by_quality(self, examples: List[Dict]) -> List[Dict]:
        """Filter examples by quality score."""
        filtered = []
        
        for example in examples:
            quality_score = example.get('metadata', {}).get('quality_score', 0)
            if quality_score >= self.min_quality:
                filtered.append(example)
        
        logger.info(f"Filtered to {len(filtered)} examples with quality >= {self.min_quality}")
        return filtered
    
    def create_train_validation_split(self, examples: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Split data into training and validation sets."""
        # Shuffle for random split
        shuffled = examples.copy()
        random.shuffle(shuffled)
        
        # Calculate split point
        val_size = int(len(shuffled) * self.validation_split)
        
        validation = shuffled[:val_size]
        training = shuffled[val_size:]
        
        logger.info(f"Split data: {len(training)} training, {len(validation)} validation")
        return training, validation
    
    def export_dataset(self, examples: List[Dict], filename: str, 
                      include_metadata: bool = False) -> str:
        """Export dataset to JSONL format."""
        output_path = self.export_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in examples:
                # Format for Ollama
                if include_metadata:
                    # Include full example with metadata
                    formatted = example
                else:
                    # Only instruction/input/output
                    formatted = {
                        'instruction': example['instruction'],
                        'input': example['input'],
                        'output': example['output']
                    }
                
                f.write(json.dumps(formatted, ensure_ascii=False) + '\n')
        
        logger.info(f"Exported {len(examples)} examples to {output_path}")
        return str(output_path)
    
    def generate_model_card(self, stats: Dict) -> str:
        """Generate model card with training information."""
        card = f"""# Rick Rubin AI Model Card

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Training Data Statistics
- Total examples: {stats['total_examples']}
- Training set: {stats['train_size']}
- Validation set: {stats['val_size']}
- Minimum quality threshold: {stats['min_quality']}
- Average quality score: {stats['avg_quality']:.1f}

## Source Distribution
{stats['source_distribution']}

## Quality Distribution
- Excellent (90+): {stats['quality_dist']['excellent']}
- Good (80-89): {stats['quality_dist']['good']}

## Training Recommendations

### Ollama Fine-tuning Command
```bash
ollama create rick-rubin -f Modelfile
```

### Suggested Modelfile
```
FROM llama3.1:8b
ADAPTER ./rick_rubin_lora.bin

PARAMETER temperature 0.8
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1

SYSTEM You are Rick Rubin, the legendary music producer. Share your wisdom about music production, creativity, and the artistic process based on your decades of experience.
```

### Training Parameters
- Learning rate: 1e-5
- Batch size: 4
- Epochs: 3
- LoRA rank: 16
- LoRA alpha: 32

## Notes
- This dataset focuses on Rick Rubin's production philosophy and creative insights
- Quality filtering ensures high-value training examples
- Varied instruction templates prevent overfitting
"""
        return card
    
    def run_export(self) -> Dict:
        """Run the complete export process."""
        # Load all training data
        all_examples = self.load_all_training_data()
        
        if not all_examples:
            logger.error("No training data found!")
            return {}
        
        # Filter by quality
        filtered_examples = self.filter_by_quality(all_examples)
        
        if not filtered_examples:
            logger.error(f"No examples meet quality threshold of {self.min_quality}")
            return {}
        
        # Create train/validation split
        train_examples, val_examples = self.create_train_validation_split(filtered_examples)
        
        # Generate filenames with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export datasets
        train_file = self.export_dataset(
            train_examples,
            f"rick_rubin_train_{timestamp}.jsonl"
        )
        
        val_file = self.export_dataset(
            val_examples,
            f"rick_rubin_val_{timestamp}.jsonl"
        )
        
        # Export full dataset with metadata (for analysis)
        full_file = self.export_dataset(
            filtered_examples,
            f"rick_rubin_full_{timestamp}_with_metadata.jsonl",
            include_metadata=True
        )
        
        # Calculate statistics
        quality_scores = [ex.get('metadata', {}).get('quality_score', 0) 
                         for ex in filtered_examples]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Source distribution
        sources = {}
        for ex in filtered_examples:
            source = ex.get('metadata', {}).get('source', 'Unknown')
            sources[source] = sources.get(source, 0) + 1
        
        source_dist = '\n'.join([f"- {source}: {count}" for source, count in 
                                sorted(sources.items(), key=lambda x: x[1], reverse=True)])
        
        # Quality distribution
        quality_dist = {
            'excellent': sum(1 for s in quality_scores if s >= 90),
            'good': sum(1 for s in quality_scores if 80 <= s < 90)
        }
        
        stats = {
            'total_examples': len(filtered_examples),
            'train_size': len(train_examples),
            'val_size': len(val_examples),
            'min_quality': self.min_quality,
            'avg_quality': avg_quality,
            'source_distribution': source_dist,
            'quality_dist': quality_dist,
            'train_file': train_file,
            'val_file': val_file,
            'full_file': full_file
        }
        
        # Generate and save model card
        model_card = self.generate_model_card(stats)
        card_path = self.export_dir / f"MODEL_CARD_{timestamp}.md"
        card_path.write_text(model_card)
        
        # Record export in database
        self.tracker.record_export(
            export_file=train_file,
            total_examples=len(train_examples),
            avg_quality=avg_quality,
            min_threshold=self.min_quality,
            sources_included=len(sources)
        )
        
        # Print summary
        print("\n" + "="*60)
        print("OLLAMA EXPORT COMPLETE")
        print("="*60)
        print(f"Training file: {train_file}")
        print(f"Validation file: {val_file}")
        print(f"Full dataset: {full_file}")
        print(f"Model card: {card_path}")
        print(f"\nTotal examples: {stats['total_examples']}")
        print(f"Average quality: {stats['avg_quality']:.1f}")
        print("\nNext steps:")
        print("1. Review the model card for training recommendations")
        print("2. Use the training file with Ollama fine-tuning")
        print("3. Validate results with the validation set")
        
        return stats


def main():
    """Run Ollama export from command line."""
    parser = argparse.ArgumentParser(description="Export data for Ollama fine-tuning")
    parser.add_argument('--min-quality', type=float, default=80.0,
                       help='Minimum quality score for inclusion')
    parser.add_argument('--validation-split', type=float, default=0.1,
                       help='Fraction of data for validation')
    
    args = parser.parse_args()
    
    # Create exporter
    exporter = OllamaExporter(
        min_quality=args.min_quality,
        validation_split=args.validation_split
    )
    
    # Run export
    stats = exporter.run_export()
    
    if not stats:
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Validate Rick Rubin training data quality."""

import json
import sys
from pathlib import Path
from typing import Dict, List
import statistics

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def validate_jsonl_file(file_path: Path) -> Dict:
    """Validate a JSONL training file."""
    stats = {
        'total_lines': 0,
        'valid_examples': 0,
        'invalid_examples': 0,
        'instruction_lengths': [],
        'input_lengths': [],
        'output_lengths': [],
        'issues': []
    }
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            stats['total_lines'] += 1
            
            try:
                # Parse JSON
                example = json.loads(line)
                
                # Check required fields
                if not all(field in example for field in ['instruction', 'input', 'output']):
                    stats['issues'].append(f"Line {line_num}: Missing required fields")
                    stats['invalid_examples'] += 1
                    continue
                
                # Check field types
                if not isinstance(example['instruction'], str):
                    stats['issues'].append(f"Line {line_num}: Instruction is not string")
                    stats['invalid_examples'] += 1
                    continue
                
                # Check lengths
                inst_len = len(example['instruction'])
                input_len = len(example['input'])
                output_len = len(example['output'])
                
                # Validate reasonable lengths
                if inst_len == 0:
                    stats['issues'].append(f"Line {line_num}: Empty instruction")
                if output_len < 10:
                    stats['issues'].append(f"Line {line_num}: Output too short ({output_len} chars)")
                if output_len > 10000:
                    stats['issues'].append(f"Line {line_num}: Output too long ({output_len} chars)")
                
                stats['instruction_lengths'].append(inst_len)
                stats['input_lengths'].append(input_len)
                stats['output_lengths'].append(output_len)
                stats['valid_examples'] += 1
                
            except json.JSONDecodeError as e:
                stats['issues'].append(f"Line {line_num}: JSON parse error - {e}")
                stats['invalid_examples'] += 1
            except Exception as e:
                stats['issues'].append(f"Line {line_num}: Unexpected error - {e}")
                stats['invalid_examples'] += 1
    
    return stats


def check_rick_rubin_content(file_path: Path, sample_size: int = 10) -> List[Dict]:
    """Sample and check content for Rick Rubin authenticity."""
    samples = []
    rick_indicators = [
        'i think', 'i believe', 'i feel', 'when i produced',
        'johnny cash', 'red hot chili peppers', 'less is more',
        'creative', 'studio', 'album', 'production'
    ]
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        # Sample evenly throughout file
        step = max(1, len(lines) // sample_size)
        
        for i in range(0, len(lines), step):
            if i >= len(lines):
                break
                
            try:
                example = json.loads(lines[i])
                output_lower = example['output'].lower()
                
                # Count Rick indicators
                indicator_count = sum(1 for ind in rick_indicators if ind in output_lower)
                
                samples.append({
                    'line': i + 1,
                    'instruction': example['instruction'][:50] + '...',
                    'output_preview': example['output'][:150] + '...',
                    'rick_indicators': indicator_count,
                    'word_count': len(example['output'].split())
                })
                
            except:
                continue
                
            if len(samples) >= sample_size:
                break
    
    return samples


def main():
    """Validate training data files."""
    export_dir = Path("data/exports")
    
    print("="*60)
    print("TRAINING DATA VALIDATION")
    print("="*60)
    
    # Find JSONL files
    jsonl_files = list(export_dir.glob("*.jsonl"))
    
    if not jsonl_files:
        print("No JSONL files found in data/exports/")
        print("\nRun 'python scripts/batch_processor.py' first to process files")
        print("Then run 'python scripts/export_for_ollama.py' to create training files")
        return
    
    # Sort by modification time (newest first)
    jsonl_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    for file_path in jsonl_files[:3]:  # Check up to 3 most recent
        print(f"\n📄 Validating: {file_path.name}")
        print("-" * 40)
        
        # Validate structure
        stats = validate_jsonl_file(file_path)
        
        print(f"Total lines: {stats['total_lines']}")
        print(f"Valid examples: {stats['valid_examples']}")
        print(f"Invalid examples: {stats['invalid_examples']}")
        
        if stats['valid_examples'] > 0:
            # Calculate statistics
            avg_inst = statistics.mean(stats['instruction_lengths'])
            avg_input = statistics.mean(stats['input_lengths'])
            avg_output = statistics.mean(stats['output_lengths'])
            
            print(f"\nAverage lengths:")
            print(f"  - Instruction: {avg_inst:.0f} chars")
            print(f"  - Input: {avg_input:.0f} chars")
            print(f"  - Output: {avg_output:.0f} chars ({avg_output/5:.0f} words)")
            
            # Show issues if any
            if stats['issues']:
                print(f"\n⚠️  Issues found ({len(stats['issues'])} total):")
                for issue in stats['issues'][:5]:
                    print(f"  - {issue}")
                if len(stats['issues']) > 5:
                    print(f"  ... and {len(stats['issues']) - 5} more")
        
        # Check content quality
        if 'train' in file_path.name and stats['valid_examples'] > 0:
            print("\n🔍 Content Sampling:")
            samples = check_rick_rubin_content(file_path, sample_size=5)
            
            for sample in samples[:3]:
                print(f"\nLine {sample['line']}:")
                print(f"  Instruction: {sample['instruction']}")
                print(f"  Rick indicators: {sample['rick_indicators']}")
                print(f"  Word count: {sample['word_count']}")
    
    print("\n" + "="*60)
    print("✅ Validation complete!")
    print("\nIf all looks good, you're ready to fine-tune with Ollama:")
    print("1. Copy the training JSONL to your Ollama directory")
    print("2. Create a Modelfile following the MODEL_CARD recommendations")
    print("3. Run: ollama create rick-rubin -f Modelfile")


if __name__ == "__main__":
    main()
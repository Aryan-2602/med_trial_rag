#!/usr/bin/env python3
"""Batch clean all JSON files in the prompt_engineering folder.

This script processes all raw JSON files in data/prompt_engineering/
and creates cleaned versions (with _cleaned suffix).
"""

import sys
from pathlib import Path

# Import the processing function
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.process_qa_for_prompt_engineering import process_qa_file


def main():
    """Batch process all JSON files in prompt_engineering folder."""
    prompt_dir = Path("data/prompt_engineering")
    
    if not prompt_dir.exists():
        print(f"❌ Directory {prompt_dir} does not exist")
        return
    
    # Find all JSON files that don't already have _cleaned suffix
    json_files = [
        f for f in prompt_dir.glob("*.json")
        if not f.name.endswith("_cleaned.json") and not f.name.startswith("_")
    ]
    
    if not json_files:
        print(f"✅ No files to process in {prompt_dir}")
        return
    
    print(f"📁 Found {len(json_files)} file(s) to process:\n")
    for f in json_files:
        print(f"  - {f.name}")
    
    print()
    
    for json_file in json_files:
        # Create output filename with _cleaned suffix
        output_file = json_file.parent / f"{json_file.stem}_cleaned.json"
        
        # Skip if cleaned version already exists
        if output_file.exists():
            print(f"⏭️  Skipping {json_file.name} (cleaned version already exists)")
            continue
        
        print(f"\n{'='*60}")
        print(f"Processing: {json_file.name}")
        print(f"{'='*60}")
        
        try:
            process_qa_file(json_file, output_file)
        except Exception as e:
            print(f"❌ Error processing {json_file.name}: {e}")
            continue
    
    print(f"\n✅ Batch processing complete!")


if __name__ == "__main__":
    main()


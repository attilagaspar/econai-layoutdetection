import os
import json
import argparse
from pathlib import Path

#
# This script recursively processes LabelMe JSON files in a given directory,
# correcting labels based on predefined mappings from 'labels_bad' to 'labels_good'

# this script is needed because labelm_to_coco.py did not carry over the labels correctly 
# so labels were reassigned in random order before training
#

# Label correction mappings - modify these lists as needed
labels_bad = [
    "folyoiratcim",
    "kep", 
    "szovegdoboz",
    "kepalairas",
    "oldalfejlec",
    "tablazatfejlec",
    "tablazatelem",
    "rovatcim"
]

labels_good = [
    "tablazatelem",
    "tablazatfejlec",
    "oldalfejlec", 
    "folyoiratcim",
    "rovatcim",
    "kep",
    "kepalairas",
    "szovegdoboz"
]


def create_label_mapping():
    """Create a dictionary mapping bad labels to good labels."""
    if len(labels_bad) != len(labels_good):
        print(f"ERROR: labels_bad and labels_good must have the same length!")
        print(f"labels_bad has {len(labels_bad)} items, labels_good has {len(labels_good)} items")
        return None
    
    mapping = {}
    for i in range(len(labels_bad)):
        mapping[labels_bad[i]] = labels_good[i]
    
    print(f"Label mapping created:")
    for bad, good in mapping.items():
        print(f"  '{bad}' -> '{good}'")
    
    return mapping


def correct_labels_in_json(json_path, label_mapping):
    """
    Correct labels in a single LabelMe JSON file.
    
    Args:
        json_path: Path to the JSON file
        label_mapping: Dictionary mapping bad labels to good labels
    
    Returns:
        Number of labels corrected, or -1 if error
    """
    try:
        # Read the JSON file
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if this is a LabelMe JSON (should have 'shapes' key)
        if 'shapes' not in data:
            return 0  # Not a LabelMe JSON, skip silently
        
        corrections_made = 0
        
        # Process each shape
        for shape in data.get('shapes', []):
            if 'label' in shape:
                original_label = shape['label']
                if original_label in label_mapping:
                    new_label = label_mapping[original_label]
                    shape['label'] = new_label
                    corrections_made += 1
                    print(f"    Corrected: '{original_label}' -> '{new_label}'")
        
        # Save the corrected JSON if any changes were made
        if corrections_made > 0:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  Saved {corrections_made} corrections to {json_path}")
        
        return corrections_made
        
    except json.JSONDecodeError as e:
        print(f"  ERROR: Invalid JSON format in {json_path}: {e}")
        return -1
    except Exception as e:
        print(f"  ERROR: Failed to process {json_path}: {e}")
        return -1


def process_directory(input_dir, label_mapping):
    """
    Recursively process all JSON files in the input directory.
    
    Args:
        input_dir: Root directory to process
        label_mapping: Dictionary mapping bad labels to good labels
    
    Returns:
        Tuple of (total_files_processed, total_corrections_made, files_with_errors)
    """
    total_files_processed = 0
    total_corrections_made = 0
    files_with_errors = 0
    
    print(f"\nScanning directory recursively: {input_dir}")
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(input_dir):
        json_files = [f for f in files if f.lower().endswith('.json')]
        
        if json_files:
            rel_path = os.path.relpath(root, input_dir)
            if rel_path == '.':
                print(f"\nProcessing root directory:")
            else:
                print(f"\nProcessing directory: {rel_path}")
        
        for json_file in json_files:
            json_path = os.path.join(root, json_file)
            print(f"  Processing: {json_file}")
            
            corrections = correct_labels_in_json(json_path, label_mapping)
            
            if corrections == -1:
                files_with_errors += 1
            elif corrections == 0:
                print(f"    No corrections needed")
            else:
                total_corrections_made += corrections
            
            total_files_processed += 1
    
    return total_files_processed, total_corrections_made, files_with_errors


def main():
    parser = argparse.ArgumentParser(
        description="Recursively correct labels in LabelMe JSON files based on predefined mappings"
    )
    parser.add_argument("input_folder", 
                        help="Root directory to recursively search for LabelMe JSON files")
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.exists(args.input_folder):
        print(f"ERROR: Input directory does not exist: {args.input_folder}")
        return 1
    
    if not os.path.isdir(args.input_folder):
        print(f"ERROR: Input path is not a directory: {args.input_folder}")
        return 1
    
    print(f"Input directory: {args.input_folder}")
    
    # Create label mapping
    label_mapping = create_label_mapping()
    if label_mapping is None:
        return 1
    
    if not label_mapping:
        print("WARNING: No label mappings defined. Please edit the labels_bad and labels_good lists in the script.")
        return 1
    
    # Process all JSON files
    total_files, total_corrections, error_files = process_directory(args.input_folder, label_mapping)
    
    # Print summary
    print(f"\n=== SUMMARY ===")
    print(f"Total JSON files processed: {total_files}")
    print(f"Total label corrections made: {total_corrections}")
    print(f"Files with errors: {error_files}")
    
    if total_corrections > 0:
        print(f"\nSUCCESS: Applied {total_corrections} label corrections across {total_files} files")
    else:
        print(f"\nNo corrections were needed.")
    
    return 0


if __name__ == "__main__":
    main()
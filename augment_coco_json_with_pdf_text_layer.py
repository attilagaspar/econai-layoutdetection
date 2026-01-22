import os
import json
import argparse
import fitz  # PyMuPDF
from pathlib import Path


def find_coco_json(layout_folder):
    """Find COCO JSON file in the layout folder."""
    json_files = [f for f in os.listdir(layout_folder) if f.endswith('.json')]
    
    # Look for common COCO JSON naming patterns
    coco_candidates = [f for f in json_files if 'coco' in f.lower() or 'annotations' in f.lower()]
    
    if coco_candidates:
        return os.path.join(layout_folder, coco_candidates[0])
    elif json_files:
        # If no obvious COCO file, take the first JSON
        return os.path.join(layout_folder, json_files[0])
    else:
        return None


def get_page_number_from_image_id(coco_data, image_id):
    """Extract page number from image filename based on image_id."""
    for image in coco_data.get('images', []):
        if image['id'] == image_id:
            filename = image['file_name']
            # Try to extract page number from filename
            # Common patterns: page_001.jpg, image_1.jpg, etc.
            basename = os.path.splitext(os.path.basename(filename))[0]
            
            # Extract numbers from filename
            numbers = ''.join(filter(str.isdigit, basename))
            if numbers:
                # Convert to 0-based page index
                return int(numbers) - 1
            else:
                # Fallback: assume image_id corresponds to page number
                return image_id - 1
    
    # Fallback: assume image_id corresponds to page number
    return image_id - 1


def extract_text_from_bbox(pdf_doc, page_num, bbox_coco):
    """
    Extract text from PDF using COCO bounding box coordinates.
    
    Args:
        pdf_doc: PyMuPDF document object
        page_num: Page number (0-based)
        bbox_coco: COCO bbox format [x, y, width, height]
    
    Returns:
        Extracted text as string
    """
    if page_num >= pdf_doc.page_count:
        return ""
    
    page = pdf_doc[page_num]
    
    # Convert COCO bbox [x, y, width, height] to PyMuPDF rect [x0, y0, x1, y1]
    x, y, width, height = bbox_coco
    rect = fitz.Rect(x, y, x + width, y + height)
    
    # Extract text from the specified rectangle
    text = page.get_text("text", clip=rect).strip()
    
    return text


def process_pdf_layout_pair(pdf_path, layout_folder):
    """Process a single PDF and its corresponding layout folder."""
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    print(f"\n=== Processing PDF: {pdf_name} ===")
    
    # Check if layout folder exists
    if not os.path.exists(layout_folder):
        print(f"WARNING: Layout folder not found: {layout_folder}")
        return False
    
    # Find COCO JSON file
    coco_json_path = find_coco_json(layout_folder)
    if not coco_json_path:
        print(f"WARNING: No JSON file found in {layout_folder}")
        return False
    
    print(f"Found COCO JSON: {coco_json_path}")
    
    # Load COCO JSON
    try:
        with open(coco_json_path, 'r', encoding='utf-8') as f:
            coco_data = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load JSON file: {e}")
        return False
    
    # Open PDF
    try:
        pdf_doc = fitz.open(pdf_path)
        print(f"Opened PDF with {pdf_doc.page_count} pages")
    except Exception as e:
        print(f"ERROR: Failed to open PDF: {e}")
        return False
    
    # Process annotations
    annotations = coco_data.get('annotations', [])
    print(f"Processing {len(annotations)} annotations...")
    
    updated_count = 0
    
    for i, annotation in enumerate(annotations):
        if i % 50 == 0 and i > 0:
            print(f"  Processed {i}/{len(annotations)} annotations...")
        
        image_id = annotation['image_id']
        bbox = annotation['bbox']
        
        # Get page number from image_id
        page_num = get_page_number_from_image_id(coco_data, image_id)
        
        # Extract text from PDF
        try:
            extracted_text = extract_text_from_bbox(pdf_doc, page_num, bbox)
            annotation['original_pdf_text_layer'] = extracted_text
            updated_count += 1
            
            if extracted_text and len(extracted_text) > 50:
                print(f"    Annotation {annotation['id']}: Extracted {len(extracted_text)} characters")
            
        except Exception as e:
            print(f"WARNING: Failed to extract text for annotation {annotation['id']}: {e}")
            annotation['original_pdf_text_layer'] = ""
    
    pdf_doc.close()
    
    # Save updated COCO JSON
    try:
        with open(coco_json_path, 'w', encoding='utf-8') as f:
            json.dump(coco_data, f, indent=2, ensure_ascii=False)
        print(f"SUCCESS: Updated {updated_count} annotations in {coco_json_path}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to save updated JSON: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Augment COCO JSON annotations with text extracted from PDF text layer"
    )
    parser.add_argument("pdf_directory", 
                        help="Directory containing PDF files")
    parser.add_argument("layout_directory", 
                        help="Directory containing layout folders with COCO JSON files")
    
    args = parser.parse_args()
    
    # Validate directories
    if not os.path.exists(args.pdf_directory):
        print(f"ERROR: PDF directory does not exist: {args.pdf_directory}")
        return 1
    
    if not os.path.exists(args.layout_directory):
        print(f"ERROR: Layout directory does not exist: {args.layout_directory}")
        return 1
    
    print(f"PDF Directory: {args.pdf_directory}")
    print(f"Layout Directory: {args.layout_directory}")
    
    # Find all PDF files (not recursive)
    pdf_files = [f for f in os.listdir(args.pdf_directory) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("WARNING: No PDF files found in the specified directory")
        return 1
    
    print(f"\nFound {len(pdf_files)} PDF files to process")
    
    success_count = 0
    total_count = len(pdf_files)
    
    # Process each PDF
    for pdf_file in pdf_files:
        pdf_path = os.path.join(args.pdf_directory, pdf_file)
        pdf_name = os.path.splitext(pdf_file)[0]
        layout_folder = os.path.join(args.layout_directory, pdf_name)
        
        if process_pdf_layout_pair(pdf_path, layout_folder):
            success_count += 1
    
    print(f"\n=== SUMMARY ===")
    print(f"Total PDFs processed: {total_count}")
    print(f"Successfully processed: {success_count}")
    print(f"Failed: {total_count - success_count}")
    
    return 0


if __name__ == "__main__":
    main()
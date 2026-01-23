import os
import json
import argparse
import fitz  # PyMuPDF
from pathlib import Path
import re


def extract_text_from_labelme_bbox(pdf_doc, page_num, labelme_points, image_width, image_height):
    """
    Extract text from PDF using LabelMe bounding box coordinates.
    
    Args:
        pdf_doc: PyMuPDF document object
        page_num: Page number (0-based)
        labelme_points: LabelMe points format [[x1,y1], [x2,y2]]
        image_width: Original image width in pixels
        image_height: Original image height in pixels
    
    Returns:
        Extracted text as string
    """
    if page_num >= pdf_doc.page_count:
        return ""
    
    page = pdf_doc[page_num]
    pdf_rect = page.rect  # Get PDF page dimensions
    
    # Convert LabelMe image coordinates to PDF coordinates
    point1, point2 = labelme_points[0], labelme_points[1]
    
    # Get bounding box in image coordinates
    img_x0, img_y0 = min(point1[0], point2[0]), min(point1[1], point2[1])
    img_x1, img_y1 = max(point1[0], point2[0]), max(point1[1], point2[1])
    
    # Calculate scaling factors
    scale_x = pdf_rect.width / image_width
    scale_y = pdf_rect.height / image_height
    
    # Convert to PDF coordinates (scaling and coordinate system conversion)
    pdf_x0 = img_x0 * scale_x
    pdf_y0 = img_y0 * scale_y  # PDF uses same top-left origin for this conversion
    pdf_x1 = img_x1 * scale_x
    pdf_y1 = img_y1 * scale_y
    
    # Create rectangle for text extraction
    rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
    
    # Extract text from the specified rectangle
    text = page.get_text("text", clip=rect).strip()
    
    return text


def get_page_json_files(images_dir):
    """
    Get page JSON files in proper numerical order (page_1.json, page_2.json, etc.)
    
    Args:
        images_dir: Directory containing page JSON files
    
    Returns:
        List of tuples (page_number, filepath) sorted by page number
    """
    json_files = []
    
    if not os.path.exists(images_dir):
        return []
    
    for filename in os.listdir(images_dir):
        if filename.lower().endswith('.json'):
            # Extract page number using regex
            match = re.match(r'page_(\d+)\.json', filename, re.IGNORECASE)
            if match:
                page_num = int(match.group(1))
                filepath = os.path.join(images_dir, filename)
                json_files.append((page_num, filepath))
    
    # Sort by page number (not lexicographically)
    json_files.sort(key=lambda x: x[0])
    
    return json_files


def process_labelme_json(json_path, pdf_doc, page_num, verbose=True):
    """
    Process a single LabelMe JSON file and add PDF text layer information.
    
    Args:
        json_path: Path to the LabelMe JSON file
        pdf_doc: PyMuPDF document object
        page_num: PDF page number (0-based)
        verbose: Whether to print verbose output
    
    Returns:
        Number of shapes processed, or -1 if error
    """
    try:
        # Read the JSON file
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if this is a LabelMe JSON (should have 'shapes' key)
        if 'shapes' not in data:
            if verbose:
                print(f"    WARNING: Not a LabelMe JSON (no 'shapes' key): {os.path.basename(json_path)}")
            return 0
        
        # Get image dimensions from JSON
        image_width = data.get('imageWidth', 0)
        image_height = data.get('imageHeight', 0)
        
        if image_width == 0 or image_height == 0:
            if verbose:
                print(f"    WARNING: No image dimensions found in {os.path.basename(json_path)}")
            return 0
        
        shapes_processed = 0
        
        # Process each shape
        for shape in data.get('shapes', []):
            if 'points' in shape and len(shape['points']) >= 2:
                # Extract text from PDF using the shape's bounding box
                try:
                    extracted_text = extract_text_from_labelme_bbox(
                        pdf_doc, page_num, shape['points'], image_width, image_height
                    )
                    shape['original_pdf_text_layer'] = extracted_text
                    shapes_processed += 1
                    
                    if verbose and extracted_text and len(extracted_text) > 30:
                        print(f"      Shape '{shape.get('label', 'unknown')}': Extracted {len(extracted_text)} characters")
                    elif verbose and extracted_text:
                        # Show shorter text extracts
                        preview = extracted_text.replace('\n', ' ')[:50]
                        print(f"      Shape '{shape.get('label', 'unknown')}': '{preview}{'...' if len(extracted_text) > 50 else ''}'")
                    
                except Exception as e:
                    if verbose:
                        print(f"      WARNING: Failed to extract text for shape: {e}")
                    shape['original_pdf_text_layer'] = ""
            else:
                if verbose:
                    print(f"      WARNING: Shape missing valid 'points' data")
                shape['original_pdf_text_layer'] = ""
        
        # Save the updated JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        if verbose and shapes_processed > 0:
            print(f"    Updated {shapes_processed} shapes in {os.path.basename(json_path)}")
        
        return shapes_processed
        
    except json.JSONDecodeError as e:
        if verbose:
            print(f"    ERROR: Invalid JSON format in {json_path}: {e}")
        return -1
    except Exception as e:
        if verbose:
            print(f"    ERROR: Failed to process {json_path}: {e}")
        return -1


def process_pdf_layout_pair(pdf_path, layout_folder, verbose=True):
    """Process a single PDF and its corresponding layout folder."""
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    if verbose:
        print(f"\n=== Processing PDF: {pdf_name} ===")
    
    # Check if layout folder exists
    if not os.path.exists(layout_folder):
        if verbose:
            print(f"WARNING: Layout folder not found: {layout_folder}")
        return False
    
    # Check for images subfolder
    images_dir = os.path.join(layout_folder, "images")
    if not os.path.exists(images_dir):
        if verbose:
            print(f"WARNING: Images subfolder not found: {images_dir}")
        return False
    
    if verbose:
        print(f"Found images directory: {images_dir}")
    
    # Get page JSON files in proper numerical order
    page_json_files = get_page_json_files(images_dir)
    
    if not page_json_files:
        if verbose:
            print(f"WARNING: No page_X.json files found in {images_dir}")
        return False
    
    if verbose:
        print(f"Found {len(page_json_files)} page JSON files: {[f'page_{p}.json' for p, _ in page_json_files]}")
    
    # Open PDF
    try:
        pdf_doc = fitz.open(pdf_path)
        pdf_page_count = pdf_doc.page_count
        if verbose:
            print(f"Opened PDF with {pdf_page_count} pages")
    except Exception as e:
        if verbose:
            print(f"ERROR: Failed to open PDF: {e}")
        return False
    
    # Verify page count matches
    if len(page_json_files) != pdf_page_count:
        if verbose:
            print(f"WARNING: Page count mismatch! PDF has {pdf_page_count} pages, but found {len(page_json_files)} JSON files")
            print(f"This might indicate missing or extra JSON files")
    
    # Process each page JSON
    total_shapes_processed = 0
    
    for page_num_1based, json_path in page_json_files:
        page_num_0based = page_num_1based - 1  # Convert to 0-based for PDF
        
        if verbose:
            print(f"  Processing page_{page_num_1based}.json (PDF page {page_num_0based + 1})")
        
        if page_num_0based >= pdf_page_count:
            if verbose:
                print(f"    WARNING: JSON file page_{page_num_1based}.json refers to page {page_num_1based} but PDF only has {pdf_page_count} pages")
            continue
        
        shapes_processed = process_labelme_json(json_path, pdf_doc, page_num_0based, verbose)
        if shapes_processed > 0:
            total_shapes_processed += shapes_processed
    
    pdf_doc.close()
    
    if verbose:
        print(f"SUCCESS: Processed {total_shapes_processed} shapes across {len(page_json_files)} pages")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Augment LabelMe JSON annotations with text extracted from PDF text layer"
    )
    parser.add_argument("pdf_directory", 
                        help="Directory containing PDF files")
    parser.add_argument("layout_directory", 
                        help="Directory containing layout folders with LabelMe JSON files")
    parser.add_argument("--quiet", "-q", 
                        action="store_true",
                        help="Disable verbose output")
    
    args = parser.parse_args()
    
    verbose = not args.quiet
    
    # Validate directories
    if not os.path.exists(args.pdf_directory):
        print(f"ERROR: PDF directory does not exist: {args.pdf_directory}")
        return 1
    
    if not os.path.exists(args.layout_directory):
        print(f"ERROR: Layout directory does not exist: {args.layout_directory}")
        return 1
    
    if verbose:
        print(f"PDF Directory: {args.pdf_directory}")
        print(f"Layout Directory: {args.layout_directory}")
    
    # Find all PDF files (not recursive)
    pdf_files = [f for f in os.listdir(args.pdf_directory) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("WARNING: No PDF files found in the specified directory")
        return 1
    
    if verbose:
        print(f"\nFound {len(pdf_files)} PDF files to process")
    
    success_count = 0
    total_count = len(pdf_files)
    
    # Process each PDF
    for pdf_file in pdf_files:
        pdf_path = os.path.join(args.pdf_directory, pdf_file)
        pdf_name = os.path.splitext(pdf_file)[0]
        layout_folder = os.path.join(args.layout_directory, pdf_name)
        
        if process_pdf_layout_pair(pdf_path, layout_folder, verbose):
            success_count += 1
    
    if verbose:
        print(f"\n=== SUMMARY ===")
        print(f"Total PDFs processed: {total_count}")
        print(f"Successfully processed: {success_count}")
        print(f"Failed: {total_count - success_count}")
    
    return 0


if __name__ == "__main__":
    main()
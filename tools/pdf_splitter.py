#!/usr/bin/env python3
"""
PDF to JPG Converter Script

This script converts PDF files to high-resolution JPG images on a page-by-page basis.

Description:
- Takes two command-line arguments: input folder (containing PDFs) and output folder
- Recursively searches the input folder for all PDF files
- For each PDF file found, creates a corresponding subfolder in the output directory
- Converts each page of the PDF to a separate JPG image with high resolution (300 DPI)
- Names the JPG files as: {pdf_name}_page{page_number}.jpg (e.g., "document_page1.jpg")
- Maintains the directory structure from input to output folder
- Provides detailed progress information during processing

Requirements:
- pdf2image library: pip install pdf2image
- Pillow library: pip install Pillow
- poppler-utils (for pdf2image backend)
  - Windows: Download from https://github.com/oschwartz10612/poppler-windows
  - Linux: sudo apt-get install poppler-utils
  - macOS: brew install poppler

Usage:
    python pdf_to_jpg.py <input_folder> <output_folder>

Example:
    python pdf_to_jpg.py ./input_pdfs ./output_images
"""

import os
import sys
from pdf2image import convert_from_path
from PIL import Image
import argparse


def convert_pdf_to_jpg(pdf_path, output_folder, dpi=300, jpg_quality=95):
    """
    Convert a single PDF file to JPG images.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_folder (str): Directory where JPG files will be saved
        dpi (int): Resolution for the conversion (default: 300)
        jpg_quality (int): JPG compression quality 1-100 (default: 95)
    
    Returns:
        bool: True if successful, False if failed
    """
    try:
        print(f"  Converting PDF: {os.path.basename(pdf_path)}")
        
        # Convert PDF to PIL Image objects
        pages = convert_from_path(pdf_path, dpi=dpi)
        
        # Get PDF filename without extension for naming JPGs
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Save each page as JPG
        for page_num, page in enumerate(pages, start=1):
            jpg_filename = f"{pdf_name}_page{page_num}.jpg"
            jpg_path = os.path.join(output_folder, jpg_filename)
            
            # Save with high quality
            page.save(jpg_path, "JPEG", quality=jpg_quality, optimize=True)
            print(f"    Saved: {jpg_filename} ({page.size[0]}x{page.size[1]} pixels)")
        
        print(f"  ✓ Successfully converted {len(pages)} pages from {os.path.basename(pdf_path)}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error converting {os.path.basename(pdf_path)}: {str(e)}")
        return False


def process_pdfs_recursive(input_folder, output_folder, dpi=300, jpg_quality=95):
    """
    Recursively process all PDF files in the input folder.
    
    Args:
        input_folder (str): Root directory containing PDF files
        output_folder (str): Root directory for output JPG files
        dpi (int): Resolution for PDF conversion
        jpg_quality (int): JPG compression quality
    
    Returns:
        tuple: (total_pdfs_found, successful_conversions, failed_conversions)
    """
    total_pdfs = 0
    successful = 0
    failed = 0
    
    print(f"Scanning for PDF files in: {input_folder}")
    print(f"Output directory: {output_folder}")
    print("-" * 60)
    
    # Walk through all directories and subdirectories
    for root, dirs, files in os.walk(input_folder):
        # Calculate relative path to maintain directory structure
        relative_path = os.path.relpath(root, input_folder)
        if relative_path == '.':
            relative_path = ''
        
        # Process all PDF files in current directory
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        
        if pdf_files:
            print(f"\nProcessing directory: {root}")
            print(f"Found {len(pdf_files)} PDF file(s)")
        
        for pdf_file in pdf_files:
            total_pdfs += 1
            pdf_path = os.path.join(root, pdf_file)
            
            # Create corresponding output directory structure
            pdf_name = os.path.splitext(pdf_file)[0]
            if relative_path:
                pdf_output_folder = os.path.join(output_folder, relative_path, pdf_name)
            else:
                pdf_output_folder = os.path.join(output_folder, pdf_name)
            
            # Convert the PDF
            if convert_pdf_to_jpg(pdf_path, pdf_output_folder, dpi, jpg_quality):
                successful += 1
            else:
                failed += 1
    
    return total_pdfs, successful, failed


def main():
    """
    Main function to handle command-line arguments and coordinate the conversion process.
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Convert PDF files to high-resolution JPG images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pdf_to_jpg.py ./pdfs ./images
  python pdf_to_jpg.py /path/to/pdfs /path/to/output --dpi 600 --quality 90
        """
    )
    
    parser.add_argument('input_folder', help='Directory containing PDF files')
    parser.add_argument('output_folder', help='Directory for output JPG files')
    parser.add_argument('--dpi', type=int, default=300, 
                       help='Resolution for PDF conversion (default: 300)')
    parser.add_argument('--quality', type=int, default=95, choices=range(1, 101),
                       help='JPG quality 1-100 (default: 95)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate input folder
    if not os.path.exists(args.input_folder):
        print(f"Error: Input folder '{args.input_folder}' does not exist.")
        sys.exit(1)
    
    if not os.path.isdir(args.input_folder):
        print(f"Error: '{args.input_folder}' is not a directory.")
        sys.exit(1)
    
    # Create output folder if it doesn't exist
    try:
        os.makedirs(args.output_folder, exist_ok=True)
    except Exception as e:
        print(f"Error: Cannot create output folder '{args.output_folder}': {e}")
        sys.exit(1)
    
    print("PDF to JPG Converter")
    print("=" * 60)
    print(f"Input folder: {os.path.abspath(args.input_folder)}")
    print(f"Output folder: {os.path.abspath(args.output_folder)}")
    print(f"Resolution: {args.dpi} DPI")
    print(f"JPG Quality: {args.quality}%")
    print("=" * 60)
    
    # Process all PDFs
    try:
        total, successful, failed = process_pdfs_recursive(
            args.input_folder, 
            args.output_folder, 
            args.dpi, 
            args.quality
        )
        
        # Print summary
        print("\n" + "=" * 60)
        print("CONVERSION SUMMARY")
        print("=" * 60)
        print(f"Total PDF files found: {total}")
        print(f"Successfully converted: {successful}")
        print(f"Failed conversions: {failed}")
        
        if failed == 0:
            print("✓ All PDFs converted successfully!")
        else:
            print(f"⚠ {failed} PDF(s) failed to convert. Check error messages above.")
        
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nConversion interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
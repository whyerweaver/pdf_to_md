#!/usr/bin/env python3
"""
PDF to Markdown Converter

This script converts PDF files to structured Markdown with:
- Automatic table of contents with anchor links
- Section dividers and navigation links
- Clean heading structure
- VS Code compatible formatting
- Interactive file selection
- Output folder selection
- File overwrite protection

Requirements:
- pip install pypdf pdfplumber
"""

# Standard library imports
import os
import re
import argparse
from datetime import datetime
from pathlib import Path

# Third-party imports
import pdfplumber  # For better text extraction with layout
from pypdf import PdfReader  # For metadata and basic operations
import tkinter as tk
from tkinter import filedialog


def clean_text(text: str) -> str:
    """Clean extracted text for markdown conversion.
    
    Args:
        text (str): Raw text extracted from PDF
        
    Returns:
        str: Cleaned text with consistent spacing and no artifacts
    """
    # First split into lines and clean each line
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Remove multiple spaces
        line = re.sub(r'\s+', ' ', line)
        # Remove page headers/footers and other artifacts
        line = re.sub(r'Chapter \d+ -.*', '', line)
        line = re.sub(r'Page \d+', '', line)
        # Only add non-empty lines
        if line.strip():
            cleaned_lines.append(line.strip())
    
    return '\n'.join(cleaned_lines)


def extract_sections(pdf_path: str) -> list:
    """Extract sections and content from PDF.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        list: List of dictionaries containing section title, content, and anchor
    """
    sections = []
    current_section = None
    current_content = []
    
    # More flexible heading pattern that matches common heading formats
    heading_pattern = r'^[A-Z][a-zA-Z\s-]{1,50}(?:\s*[-–—]\s*[A-Z][a-zA-Z\s-]{1,50})*$'
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = clean_text(page.extract_text())
            lines = text.split('\n')
            
            for line in lines:
                # Identify section headers
                if re.match(heading_pattern, line.strip()):
                    if current_section:
                        sections.append({
                            'title': current_section,
                            'content': '\n'.join(current_content),
                            'anchor': create_anchor(current_section)
                        })
                    current_section = line.strip()
                    current_content = []
                else:
                    if current_section:
                        current_content.append(line)
    
    if current_section:
        sections.append({
            'title': current_section,
            'content': '\n'.join(current_content),
            'anchor': create_anchor(current_section)
        })
    
    return sections


def create_anchor(text: str) -> str:
    """Create GitHub-style anchor links from headings.
    
    Args:
        text (str): Heading text to convert to anchor
        
    Returns:
        str: URL-friendly anchor string
    """
    anchor = text.lower()
    anchor = re.sub(r'[^\w\s-]', '', anchor)
    anchor = re.sub(r'\s+', '-', anchor)
    return anchor


def generate_toc(sections: list) -> str:
    """Generate table of contents with anchor links.
    
    Args:
        sections (list): List of section dictionaries
        
    Returns:
        str: Markdown formatted table of contents
    """
    toc = ["## Contents\n"]
    for section in sections:
        toc.append(f"- [{section['title']}](#{section['anchor']})")
    return '\n'.join(toc)


def get_file_paths() -> tuple:
    """Get input PDF and output folder paths using GUI dialogs.
    
    Returns:
        tuple: (pdf_path, output_folder)
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get input PDF
    pdf_path = filedialog.askopenfilename(
        title="Select PDF file",
        filetypes=[("PDF files", "*.pdf")],
        initialdir=script_dir  # Set initial directory to script location
    )
    if not pdf_path:
        print("No file selected. Exiting...")
        exit()
    
    # Get output folder
    output_folder = filedialog.askdirectory(
        title="Select output folder",
        initialdir=script_dir  # Set initial directory to script location
    )
    if not output_folder:
        print("No output folder selected. Exiting...")
        exit()
    
    return pdf_path, output_folder


def get_unique_output_path(output_folder: str, base_filename: str) -> Path:
    """Generate unique output path with numbering or timestamp.
    
    Args:
        output_folder (str): Directory to save the file
        base_filename (str): Base name for the output file
        
    Returns:
        Path: Path object for the unique output file
    """
    # Ensure base_filename doesn't have an extension
    base_filename = Path(base_filename).stem
    base_path = Path(output_folder) / base_filename
    
    # Get current date in MMM_DD format
    date_str = datetime.now().strftime("%b_%d")
    
    # Try with letter suffix (a, b, c, etc.)
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        output_path = base_path.parent / f"{base_path.stem} ({letter}_{date_str}).md"
        if not output_path.exists():
            return output_path
    
    # If we run out of letters, use timestamp
    timestamp = datetime.now().strftime("%H%M%S")
    return base_path.parent / f"{base_path.stem} ({timestamp}_{date_str}).md"


def convert_to_markdown(pdf_path: str, output_path: str = None) -> str:
    """Convert PDF to markdown with structure and navigation.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_path (str, optional): Path to save the markdown file
        
    Returns:
        str: Success message or markdown content
    """
    # Extract basic metadata
    with open(pdf_path, 'rb') as f:
        pdf = PdfReader(f)
        title = pdf.metadata.title if pdf.metadata.title else Path(pdf_path).stem
    
    # Extract sections
    sections = extract_sections(pdf_path)
    
    # Generate markdown
    markdown = [f"# {title}"]
    markdown.append(generate_toc(sections))
    markdown.append("\n---\n")
    
    # Add each section with proper formatting
    for section in sections:
        markdown.append(f"## {section['title']}")
        markdown.append(section['content'])
        markdown.append(f"\n[Back to top](#contents)\n")
        markdown.append("\n---\n")
    
    # Write to output file or return as string
    markdown_text = '\n\n'.join(markdown)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        return f"Markdown saved to {output_path}"
    else:
        return markdown_text


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Convert PDF to structured Markdown')
    parser.add_argument('--cli', action='store_true', help='Use command line arguments instead of GUI')
    parser.add_argument('pdf_path', nargs='?', help='Path to the PDF file (required in CLI mode)')
    parser.add_argument('-o', '--output', help='Output markdown file path (required in CLI mode)')
    args = parser.parse_args()
    
    if args.cli:
        if not args.pdf_path:
            parser.error("PDF path is required in CLI mode")
        output_path = args.output or Path(args.pdf_path).with_suffix('.md')
    else:
        # Use GUI mode
        pdf_path, output_folder = get_file_paths()
        output_path = get_unique_output_path(
            output_folder,
            Path(pdf_path).stem
        )
    
    result = convert_to_markdown(pdf_path, output_path)
    print(result)


if __name__ == "__main__":
    main()
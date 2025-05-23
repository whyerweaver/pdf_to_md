#!/usr/bin/env python3
"""
PDF to Markdown Converter

This script converts PDF files to structured Markdown with:
- Automatic table of contents with anchor links
- Section dividers and navigation links
- Clean heading structure
- VS Code compatible formatting

Requirements:
- pip install pypdf pdfplumber
"""

import os
import re
import argparse
from pathlib import Path
import pdfplumber  # For better text extraction with layout
from pypdf import PdfReader  # For metadata and basic operations


def clean_text(text):
    """Clean extracted text for markdown conversion."""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove page headers/footers and other artifacts (customize as needed)
    text = re.sub(r'Chapter \d+ -.*\n', '', text)
    # Remove lines containing '[Instructor]'
    text = re.sub(r'^.*\[Instructor\].*$', '', text, flags=re.MULTILINE)
    return text.strip()


def extract_sections(pdf_path):
    """Extract sections and content from PDF."""
    sections = []
    current_section = None
    current_content = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Find the largest font size on this page
            max_font_size = 0
            for char in page.chars:
                if char.get("size", 0) > max_font_size:
                    max_font_size = char["size"]
            # Build a mapping of line top positions to lines
            text = page.extract_text()
            lines = text.split('\n')
            line_tops = {}
            for word in page.extract_words():
                top = int(word['top'])
                line_tops.setdefault(top, []).append(word['text'])
            # For each line, check if it is a section header
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                # Check if previous and next lines are blank
                prev_blank = (i > 0 and not lines[i-1].strip())
                next_blank = (i < len(lines)-1 and not lines[i+1].strip())
                is_surrounded_by_blank = prev_blank and next_blank
                # Check if this line is mostly in the largest font size
                is_large_font = False
                is_bold = False
                for top, words in line_tops.items():
                    if ' '.join(words).strip() == stripped_line:
                        # Get all chars at this top position
                        chars_in_line = [c for c in page.chars if int(c['top']) == top]
                        if chars_in_line:
                            large_count = sum(1 for c in chars_in_line if c['size'] == max_font_size)
                            if large_count / len(chars_in_line) > 0.7:
                                is_large_font = True
                            # Check for bold font (fontname often contains 'Bold')
                            bold_count = sum(1 for c in chars_in_line if 'Bold' in c.get('fontname', ''))
                            if bold_count / len(chars_in_line) > 0.7:
                                is_bold = True
                        break
                # Section header if regex, whitespace, large font, or bold
                if (
                    re.match(r'^[A-Z][\w\s:-]{3,60}$', stripped_line)
                    or (stripped_line and is_surrounded_by_blank)
                    or (stripped_line and is_large_font)
                    or (stripped_line and is_bold)
                ):
                    if current_section:
                        sections.append({
                            'title': current_section,
                            'content': '\n'.join(current_content),
                            'anchor': create_anchor(current_section)
                        })
                    current_section = stripped_line
                    current_content = []
                else:
                    if current_section:
                        current_content.append(line)
    
    # Add the last section
    if current_section:
        sections.append({
            'title': current_section,
            'content': '\n'.join(current_content),
            'anchor': create_anchor(current_section)
        })
    
    return sections


def create_anchor(text):
    """Create GitHub-style anchor links from headings."""
    anchor = text.lower()
    anchor = re.sub(r'[^\w\s-]', '', anchor)
    anchor = re.sub(r'\s+', '-', anchor)
    return anchor


def generate_toc(sections):
    """Generate table of contents with anchor links."""
    toc = ["## Contents\n"]
    for section in sections:
        toc.append(f"- [{section['title']}](#{section['anchor']})")
    return '\n'.join(toc)


def convert_to_markdown(pdf_path, output_path=None):
    """Convert PDF to markdown with structure and navigation."""
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


def main():
    parser = argparse.ArgumentParser(description='Convert PDF to structured Markdown')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('-o', '--output', help='Output markdown file path')
    args = parser.parse_args()
    
    # Determine output path if not specified
    output_path = args.output
    if not output_path:
        output_path = Path(args.pdf_path).with_suffix('.md')
    
    result = convert_to_markdown(args.pdf_path, output_path)
    print(result)


if __name__ == "__main__":
    main()

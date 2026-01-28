"""PDF Parser module for extracting content from PDF files"""

import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional
from paper2chunk.models import Document, DocumentMetadata, Section
import re


class PDFParser:
    """Parser for PDF documents using PyMuPDF"""
    
    def __init__(self):
        self.doc = None
        
    def parse(self, pdf_path: str) -> Document:
        """Parse a PDF file and extract structured content
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Document object with parsed content
        """
        self.doc = fitz.open(pdf_path)
        
        # Extract metadata
        metadata = self._extract_metadata()
        
        # Extract raw text
        raw_text = self._extract_text()
        
        # Extract structured content with sections
        structured_content = self._extract_structured_content()
        
        # Extract images and charts
        images = self._extract_images()
        
        document = Document(
            metadata=metadata,
            raw_text=raw_text,
            structured_content=structured_content,
            images=images,
        )
        
        self.doc.close()
        return document
    
    def _extract_metadata(self) -> DocumentMetadata:
        """Extract document metadata"""
        meta = self.doc.metadata
        
        return DocumentMetadata(
            title=meta.get("title", "Untitled Document"),
            author=meta.get("author"),
            publish_date=meta.get("creationDate"),
            source=self.doc.name,
            total_pages=len(self.doc),
        )
    
    def _extract_text(self) -> str:
        """Extract all text from the document"""
        text_parts = []
        for page_num, page in enumerate(self.doc):
            text = page.get_text()
            text_parts.append(text)
        return "\n\n".join(text_parts)
    
    def _extract_structured_content(self) -> List[Dict[str, Any]]:
        """Extract structured content with section information"""
        structured = []
        
        for page_num, page in enumerate(self.doc):
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    text = ""
                    font_size = 0
                    
                    for span in line["spans"]:
                        text += span["text"]
                        font_size = max(font_size, span["size"])
                    
                    text = text.strip()
                    if not text:
                        continue
                    
                    # Determine if this is likely a heading based on font size and formatting
                    is_heading = self._is_likely_heading(text, font_size)
                    level = self._determine_heading_level(font_size) if is_heading else 0
                    
                    structured.append({
                        "text": text,
                        "page": page_num + 1,
                        "font_size": font_size,
                        "is_heading": is_heading,
                        "level": level,
                    })
        
        return structured
    
    def _is_likely_heading(self, text: str, font_size: float) -> bool:
        """Determine if text is likely a heading"""
        # Heuristics for heading detection
        if font_size > 12:  # Larger font size
            return True
        
        # Check for common heading patterns
        heading_patterns = [
            r'^Chapter\s+\d+',
            r'^\d+\.\s+\w+',  # 1. Introduction
            r'^[IVX]+\.\s+\w+',  # Roman numerals
            r'^Abstract$',
            r'^Introduction$',
            r'^Conclusion$',
            r'^References$',
        ]
        
        for pattern in heading_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _determine_heading_level(self, font_size: float) -> int:
        """Determine heading level based on font size"""
        if font_size >= 18:
            return 1  # Chapter/main heading
        elif font_size >= 14:
            return 2  # Section
        elif font_size >= 12:
            return 3  # Subsection
        else:
            return 4  # Sub-subsection
    
    def _extract_images(self) -> List[Dict[str, Any]]:
        """Extract images and charts from the document"""
        images = []
        
        for page_num, page in enumerate(self.doc):
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = self.doc.extract_image(xref)
                
                images.append({
                    "page": page_num + 1,
                    "index": img_index,
                    "xref": xref,
                    "width": base_image["width"],
                    "height": base_image["height"],
                    "image_data": base_image["image"],
                })
        
        return images

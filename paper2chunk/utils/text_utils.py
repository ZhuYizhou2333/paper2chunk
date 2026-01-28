"""Utility functions for paper2chunk"""

import re
from typing import List


def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace and formatting"""
    # Remove multiple spaces
    text = re.sub(r' +', ' ', text)
    
    # Remove multiple newlines
    text = re.sub(r'\n\n+', '\n\n', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def extract_section_number(text: str) -> tuple[bool, str]:
    """Extract section number from text
    
    Returns:
        Tuple of (is_numbered_section, section_number)
    """
    # Match patterns like "1.2.3", "1.", "Chapter 1", etc.
    patterns = [
        r'^(\d+(?:\.\d+)*)\s+',  # 1.2.3 Title
        r'^Chapter\s+(\d+)',  # Chapter 1
        r'^Section\s+(\d+)',  # Section 1
        r'^([IVX]+)\.\s+',  # Roman numerals
    ]
    
    for pattern in patterns:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            return True, match.group(1)
    
    return False, ""


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def count_words(text: str) -> int:
    """Count words in text"""
    return len(re.findall(r'\b\w+\b', text))


def split_sentences(text: str) -> List[str]:
    """Split text into sentences"""
    # Simple sentence splitter
    sentences = re.split(r'[.!?]+\s+', text)
    return [s.strip() for s in sentences if s.strip()]

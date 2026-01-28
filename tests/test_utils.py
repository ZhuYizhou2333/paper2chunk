"""Tests for utility functions"""

import pytest
from paper2chunk.utils import (
    clean_text,
    extract_section_number,
    truncate_text,
    count_words,
    split_sentences,
)


class TestTextUtils:
    """Test cases for text utilities"""
    
    def test_clean_text(self):
        """Test text cleaning"""
        text = "This  is   text\n\n\nwith   extra   spaces"
        result = clean_text(text)
        
        assert "  " not in result
        assert "\n\n\n" not in result
    
    def test_extract_section_number(self):
        """Test section number extraction"""
        # Numbered sections
        is_num, num = extract_section_number("1.2.3 Title")
        assert is_num == True
        assert num == "1.2.3"
        
        # Chapter
        is_num, num = extract_section_number("Chapter 5")
        assert is_num == True
        assert num == "5"
        
        # Not numbered
        is_num, num = extract_section_number("Introduction")
        assert is_num == False
    
    def test_truncate_text(self):
        """Test text truncation"""
        text = "This is a long text that needs to be truncated"
        result = truncate_text(text, 20)
        
        assert len(result) <= 20
        assert result.endswith("...")
    
    def test_count_words(self):
        """Test word counting"""
        text = "This is a test with five words"
        assert count_words(text) == 7
    
    def test_split_sentences(self):
        """Test sentence splitting"""
        text = "This is sentence one. This is sentence two! Is this three?"
        sentences = split_sentences(text)
        
        assert len(sentences) == 3
        assert "one" in sentences[0]

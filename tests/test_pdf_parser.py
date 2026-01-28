"""Tests for PDF parser"""

import pytest
from paper2chunk.core.pdf_parser import PDFParser
from paper2chunk.models import Document


class TestPDFParser:
    """Test cases for PDFParser"""
    
    def test_parser_initialization(self):
        """Test parser can be initialized"""
        parser = PDFParser()
        assert parser is not None
    
    def test_is_likely_heading(self):
        """Test heading detection"""
        parser = PDFParser()
        
        # Should be detected as heading
        assert parser._is_likely_heading("Introduction", 16.0) == True
        assert parser._is_likely_heading("Chapter 1", 14.0) == True
        assert parser._is_likely_heading("1. Introduction", 12.0) == True
        
        # Should not be detected as heading
        assert parser._is_likely_heading("This is regular text", 11.0) == False
    
    def test_determine_heading_level(self):
        """Test heading level determination"""
        parser = PDFParser()
        
        assert parser._determine_heading_level(18.0) == 1
        assert parser._determine_heading_level(14.0) == 2
        assert parser._determine_heading_level(12.0) == 3
        assert parser._determine_heading_level(10.0) == 4

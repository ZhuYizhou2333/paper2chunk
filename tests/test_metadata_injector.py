"""Tests for metadata injector"""

import pytest
from paper2chunk.core.metadata_injector import MetadataInjector
from paper2chunk.models import Chunk, ChunkMetadata


class TestMetadataInjector:
    """Test cases for MetadataInjector"""
    
    def test_injector_initialization(self):
        """Test injector can be initialized"""
        injector = MetadataInjector()
        assert injector is not None
    
    def test_inject_metadata(self):
        """Test metadata injection"""
        injector = MetadataInjector()
        
        # Create a test chunk
        metadata = ChunkMetadata(
            chunk_id="test-123",
            document_title="Test Document",
            section_hierarchy=["Chapter 1", "Section 1.1"],
            page_numbers=[1, 2, 3],
            publish_date="2024-01-01",
            chunk_index=0,
            total_chunks=10,
        )
        
        chunk = Chunk(
            content="This is test content.",
            metadata=metadata,
        )
        
        # Inject metadata
        result = injector.inject_metadata([chunk])
        
        assert len(result) == 1
        assert result[0].enhanced_content is not None
        assert "Test Document" in result[0].enhanced_content
        assert "This is test content." in result[0].enhanced_content
    
    def test_format_page_numbers(self):
        """Test page number formatting"""
        injector = MetadataInjector()
        
        # Single page
        assert injector._format_page_numbers([1]) == "1"
        
        # Consecutive pages
        assert injector._format_page_numbers([1, 2, 3]) == "1-3"
        
        # Non-consecutive pages
        assert injector._format_page_numbers([1, 3, 5]) == "1, 3, 5"
        
        # Mixed
        assert injector._format_page_numbers([1, 2, 3, 5, 6, 8]) == "1-3, 5-6, 8"

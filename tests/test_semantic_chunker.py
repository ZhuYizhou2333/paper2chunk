"""Tests for semantic chunker"""

import pytest
from paper2chunk.core.semantic_chunker import SemanticChunker
from paper2chunk.config import ChunkingConfig
from paper2chunk.models import Document, DocumentMetadata


class TestSemanticChunker:
    """Test cases for SemanticChunker"""
    
    def test_chunker_initialization(self):
        """Test chunker can be initialized"""
        config = ChunkingConfig()
        chunker = SemanticChunker(config)
        assert chunker is not None
        assert chunker.config.max_chunk_size == 1000
    
    def test_chunk_raw_text(self):
        """Test chunking raw text"""
        config = ChunkingConfig(max_chunk_size=100, min_chunk_size=20)
        chunker = SemanticChunker(config)
        
        # Create a simple document
        doc = Document(
            metadata=DocumentMetadata(title="Test Document"),
            raw_text="This is a test document. " * 50,  # Long text
            structured_content=[],
            images=[],
        )
        
        chunks = chunker._chunk_raw_text(doc)
        assert len(chunks) > 0
        
        # Verify chunks respect size constraints
        for chunk in chunks:
            assert len(chunk.content) >= config.min_chunk_size
    
    def test_create_chunk(self):
        """Test chunk creation"""
        config = ChunkingConfig()
        chunker = SemanticChunker(config)
        
        chunk = chunker._create_chunk(
            content="Test content",
            document_title="Test Doc",
            section_hierarchy=["Chapter 1", "Section 1.1"],
            page_numbers=[1, 2],
            publish_date="2024-01-01"
        )
        
        assert chunk.content == "Test content"
        assert chunk.metadata.document_title == "Test Doc"
        assert len(chunk.metadata.section_hierarchy) == 2
        assert chunk.metadata.page_numbers == [1, 2]

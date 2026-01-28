"""Tests for output formatters"""

import pytest
from paper2chunk.output_formatters import (
    LightRAGFormatter,
    LangChainFormatter,
    MarkdownFormatter,
    JSONFormatter,
)
from paper2chunk.models import Chunk, ChunkMetadata


class TestFormatters:
    """Test cases for output formatters"""
    
    def create_test_chunk(self):
        """Create a test chunk"""
        metadata = ChunkMetadata(
            chunk_id="test-123",
            document_title="Test Document",
            section_hierarchy=["Chapter 1"],
            page_numbers=[1, 2],
            publish_date="2024-01-01",
            chunk_index=0,
            total_chunks=5,
        )
        
        return Chunk(
            content="Test content",
            metadata=metadata,
            entities=["Entity1", "Entity2"],
            keywords=["keyword1", "keyword2"],
        )
    
    def test_lightrag_formatter(self):
        """Test LightRAG formatter"""
        formatter = LightRAGFormatter()
        chunk = self.create_test_chunk()
        
        result = formatter.format([chunk])
        
        assert len(result) == 1
        assert result[0]["id"] == "test-123"
        assert result[0]["content"] == "Test content"
        assert "document_title" in result[0]["metadata"]
        assert result[0]["entities"] == ["Entity1", "Entity2"]
    
    def test_langchain_formatter(self):
        """Test LangChain formatter"""
        formatter = LangChainFormatter()
        chunk = self.create_test_chunk()
        
        result = formatter.format([chunk])
        
        assert len(result) == 1
        assert result[0]["page_content"] == "Test content"
        assert "metadata" in result[0]
        assert result[0]["metadata"]["source"] == "Test Document"
    
    def test_markdown_formatter(self):
        """Test Markdown formatter"""
        formatter = MarkdownFormatter()
        chunk = self.create_test_chunk()
        
        result = formatter.format([chunk])
        
        assert "## Chunk 1 of 5" in result
        assert "Test Document" in result
        assert "Test content" in result
    
    def test_json_formatter(self):
        """Test JSON formatter"""
        formatter = JSONFormatter()
        chunk = self.create_test_chunk()
        
        result = formatter.format([chunk])
        
        assert len(result) == 1
        assert result[0]["content"] == "Test content"

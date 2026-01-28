"""Output formatters for RAG systems"""

from typing import List, Dict, Any
from paper2chunk.models import Chunk
import json


class BaseFormatter:
    """Base class for output formatters"""
    
    def format(self, chunks: List[Chunk]) -> Any:
        """Format chunks for output"""
        raise NotImplementedError


class LightRAGFormatter(BaseFormatter):
    """Format chunks for LightRAG (Graph RAG) systems"""
    
    def format(self, chunks: List[Chunk]) -> List[Dict[str, Any]]:
        """Format chunks for LightRAG
        
        LightRAG expects documents with rich metadata for entity extraction
        and relationship building.
        """
        formatted = []
        
        for chunk in chunks:
            # Use enhanced content if available, otherwise use original
            content = chunk.enhanced_content if chunk.enhanced_content else chunk.content
            
            formatted_chunk = {
                "id": chunk.metadata.chunk_id,
                "content": content,
                "metadata": {
                    "document_title": chunk.metadata.document_title,
                    "section_hierarchy": chunk.metadata.section_hierarchy,
                    "page_numbers": chunk.metadata.page_numbers,
                    "publish_date": chunk.metadata.publish_date,
                    "chunk_index": chunk.metadata.chunk_index,
                    "total_chunks": chunk.metadata.total_chunks,
                },
                "entities": chunk.entities,
                "keywords": chunk.keywords,
            }
            
            formatted.append(formatted_chunk)
        
        return formatted
    
    def to_json(self, chunks: List[Chunk], output_path: str):
        """Save formatted chunks to JSON file"""
        formatted = self.format(chunks)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(formatted, f, indent=2, ensure_ascii=False)


class LangChainFormatter(BaseFormatter):
    """Format chunks for LangChain"""
    
    def format(self, chunks: List[Chunk]) -> List[Dict[str, Any]]:
        """Format chunks for LangChain Document format"""
        formatted = []
        
        for chunk in chunks:
            # Use enhanced content if available
            content = chunk.enhanced_content if chunk.enhanced_content else chunk.content
            
            # LangChain Document format
            formatted_chunk = {
                "page_content": content,
                "metadata": {
                    "source": chunk.metadata.document_title,
                    "chunk_id": chunk.metadata.chunk_id,
                    "section_hierarchy": " > ".join(chunk.metadata.section_hierarchy),
                    "page_numbers": chunk.metadata.page_numbers,
                    "publish_date": chunk.metadata.publish_date,
                    "chunk_index": chunk.metadata.chunk_index,
                    "entities": chunk.entities,
                    "keywords": chunk.keywords,
                }
            }
            
            formatted.append(formatted_chunk)
        
        return formatted
    
    def to_json(self, chunks: List[Chunk], output_path: str):
        """Save formatted chunks to JSON file"""
        formatted = self.format(chunks)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(formatted, f, indent=2, ensure_ascii=False)


class MarkdownFormatter(BaseFormatter):
    """Format chunks as Markdown documents"""
    
    def format(self, chunks: List[Chunk]) -> str:
        """Format chunks as a single Markdown document"""
        md_parts = []
        
        for i, chunk in enumerate(chunks):
            md_parts.append(f"## Chunk {i + 1} of {chunk.metadata.total_chunks}")
            md_parts.append("")
            
            # Metadata section
            md_parts.append("### Metadata")
            md_parts.append(f"- **Document**: {chunk.metadata.document_title}")
            
            if chunk.metadata.section_hierarchy:
                hierarchy = " → ".join(chunk.metadata.section_hierarchy)
                md_parts.append(f"- **Section**: {hierarchy}")
            
            if chunk.metadata.page_numbers:
                pages = ", ".join(map(str, chunk.metadata.page_numbers))
                md_parts.append(f"- **Pages**: {pages}")
            
            if chunk.metadata.publish_date:
                md_parts.append(f"- **Date**: {chunk.metadata.publish_date}")
            
            md_parts.append("")
            
            # Content section
            md_parts.append("### Content")
            content = chunk.enhanced_content if chunk.enhanced_content else chunk.content
            md_parts.append(content)
            md_parts.append("")
            
            # Entities and keywords if available
            if chunk.entities or chunk.keywords:
                md_parts.append("### Extracted Information")
                if chunk.entities:
                    md_parts.append(f"**Entities**: {', '.join(chunk.entities)}")
                if chunk.keywords:
                    md_parts.append(f"**Keywords**: {', '.join(chunk.keywords)}")
                md_parts.append("")
            
            md_parts.append("---")
            md_parts.append("")
        
        return "\n".join(md_parts)
    
    def to_file(self, chunks: List[Chunk], output_path: str):
        """Save formatted chunks to Markdown file"""
        content = self.format(chunks)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)


class JSONFormatter(BaseFormatter):
    """Format chunks as plain JSON"""
    
    def format(self, chunks: List[Chunk]) -> List[Dict[str, Any]]:
        """Format chunks as plain JSON"""
        return [chunk.model_dump() for chunk in chunks]
    
    def to_json(self, chunks: List[Chunk], output_path: str):
        """Save formatted chunks to JSON file"""
        formatted = self.format(chunks)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(formatted, f, indent=2, ensure_ascii=False)

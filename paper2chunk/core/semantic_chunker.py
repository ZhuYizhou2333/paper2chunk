"""Semantic chunking based on document structure"""

from typing import List, Dict, Any
from paper2chunk.models import Chunk, ChunkMetadata, Document
from paper2chunk.config import ChunkingConfig
import uuid


class SemanticChunker:
    """Chunk documents based on semantic structure"""
    
    def __init__(self, config: ChunkingConfig):
        self.config = config
    
    def chunk_document(self, document: Document) -> List[Chunk]:
        """Chunk a document based on its structure
        
        Args:
            document: The document to chunk
            
        Returns:
            List of semantic chunks
        """
        chunks = []
        
        if not document.structured_content:
            # Fallback to simple text chunking
            chunks = self._chunk_raw_text(document)
        else:
            # Semantic chunking based on structure
            chunks = self._chunk_structured_content(document)
        
        # Update total chunks count in metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata.chunk_index = i
            chunk.metadata.total_chunks = len(chunks)
        
        return chunks
    
    def _chunk_structured_content(self, document: Document) -> List[Chunk]:
        """Chunk based on document structure"""
        chunks = []
        current_chunk_text = []
        current_section_hierarchy = []
        current_pages = set()
        
        for item in document.structured_content:
            text = item["text"]
            page = item["page"]
            is_heading = item["is_heading"]
            level = item["level"]
            
            # If we encounter a heading, it might be time to create a new chunk
            if is_heading and current_chunk_text:
                # Create chunk from accumulated text
                chunk_text = "\n".join(current_chunk_text).strip()
                if len(chunk_text) >= self.config.min_chunk_size:
                    chunks.append(self._create_chunk(
                        chunk_text,
                        document.metadata.title,
                        current_section_hierarchy.copy(),
                        sorted(list(current_pages)),
                        document.metadata.publish_date,
                    ))
                    
                    # Start new chunk with overlap if configured
                    if self.config.overlap_size > 0 and current_chunk_text:
                        overlap_text = current_chunk_text[-1][-self.config.overlap_size:]
                        current_chunk_text = [overlap_text]
                    else:
                        current_chunk_text = []
                    current_pages = set()
            
            # Update section hierarchy
            if is_heading:
                # Adjust hierarchy based on level
                if level <= len(current_section_hierarchy):
                    current_section_hierarchy = current_section_hierarchy[:level-1]
                current_section_hierarchy.append(text)
            
            # Add text to current chunk
            current_chunk_text.append(text)
            current_pages.add(page)
            
            # Check if current chunk exceeds max size
            current_text = "\n".join(current_chunk_text)
            if len(current_text) >= self.config.max_chunk_size and not is_heading:
                chunks.append(self._create_chunk(
                    current_text,
                    document.metadata.title,
                    current_section_hierarchy.copy(),
                    sorted(list(current_pages)),
                    document.metadata.publish_date,
                ))
                
                # Start new chunk with overlap
                if self.config.overlap_size > 0 and current_chunk_text:
                    overlap_text = current_chunk_text[-1][-self.config.overlap_size:]
                    current_chunk_text = [overlap_text]
                else:
                    current_chunk_text = []
                current_pages = set()
        
        # Add final chunk
        if current_chunk_text:
            chunk_text = "\n".join(current_chunk_text).strip()
            if len(chunk_text) >= self.config.min_chunk_size:
                chunks.append(self._create_chunk(
                    chunk_text,
                    document.metadata.title,
                    current_section_hierarchy.copy(),
                    sorted(list(current_pages)),
                    document.metadata.publish_date,
                ))
        
        return chunks
    
    def _chunk_raw_text(self, document: Document) -> List[Chunk]:
        """Fallback: chunk raw text when no structure is available"""
        chunks = []
        text = document.raw_text
        
        start = 0
        while start < len(text):
            end = start + self.config.max_chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending
                for delimiter in ['. ', '.\n', '! ', '?\n']:
                    last_delimiter = text[start:end].rfind(delimiter)
                    if last_delimiter > self.config.min_chunk_size:
                        end = start + last_delimiter + len(delimiter)
                        break
            
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) >= self.config.min_chunk_size:
                chunks.append(self._create_chunk(
                    chunk_text,
                    document.metadata.title,
                    [],
                    [],
                    document.metadata.publish_date,
                ))
            
            # Move to next chunk with overlap
            start = end - self.config.overlap_size if self.config.overlap_size > 0 else end
        
        return chunks
    
    def _create_chunk(
        self,
        content: str,
        document_title: str,
        section_hierarchy: List[str],
        page_numbers: List[int],
        publish_date: str = None,
    ) -> Chunk:
        """Create a chunk with metadata"""
        chunk_id = str(uuid.uuid4())
        
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            document_title=document_title,
            section_hierarchy=section_hierarchy,
            page_numbers=page_numbers,
            publish_date=publish_date,
            chunk_index=0,  # Will be updated later
            total_chunks=0,  # Will be updated later
        )
        
        return Chunk(
            content=content,
            metadata=metadata,
        )

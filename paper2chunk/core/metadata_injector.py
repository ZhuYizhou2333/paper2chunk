"""Metadata injection for chunks"""

from typing import List
from paper2chunk.models import Chunk


class MetadataInjector:
    """Inject metadata into chunks to make them self-contained"""
    
    def inject_metadata(self, chunks: List[Chunk]) -> List[Chunk]:
        """Inject metadata into chunk content
        
        Args:
            chunks: List of chunks to enhance with metadata
            
        Returns:
            Chunks with metadata injected into content
        """
        enhanced_chunks = []
        
        for chunk in chunks:
            enhanced_content = self._inject_into_content(chunk)
            chunk.enhanced_content = enhanced_content
            enhanced_chunks.append(chunk)
        
        return enhanced_chunks
    
    def _inject_into_content(self, chunk: Chunk) -> str:
        """Inject metadata as header in the content"""
        metadata_header = self._build_metadata_header(chunk)
        
        # Combine metadata header with content
        enhanced_content = f"{metadata_header}\n\n{chunk.content}"
        
        return enhanced_content
    
    def _build_metadata_header(self, chunk: Chunk) -> str:
        """Build metadata header for a chunk"""
        header_parts = []
        
        # Document title
        header_parts.append(f"📄 **Document**: {chunk.metadata.document_title}")
        
        # Section hierarchy
        if chunk.metadata.section_hierarchy:
            hierarchy_str = " → ".join(chunk.metadata.section_hierarchy)
            header_parts.append(f"📍 **Section**: {hierarchy_str}")
        
        # Publication date
        if chunk.metadata.publish_date:
            header_parts.append(f"📅 **Date**: {chunk.metadata.publish_date}")
        
        # Page numbers
        if chunk.metadata.page_numbers:
            pages_str = self._format_page_numbers(chunk.metadata.page_numbers)
            header_parts.append(f"📖 **Pages**: {pages_str}")
        
        # Chunk position
        header_parts.append(
            f"🔢 **Chunk**: {chunk.metadata.chunk_index + 1} of {chunk.metadata.total_chunks}"
        )
        
        return "\n".join(header_parts)
    
    def _format_page_numbers(self, page_numbers: List[int]) -> str:
        """Format page numbers in a readable way"""
        if not page_numbers:
            return "N/A"
        
        if len(page_numbers) == 1:
            return str(page_numbers[0])
        
        # Group consecutive pages
        ranges = []
        start = page_numbers[0]
        end = page_numbers[0]
        
        for i in range(1, len(page_numbers)):
            if page_numbers[i] == end + 1:
                end = page_numbers[i]
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = page_numbers[i]
                end = page_numbers[i]
        
        # Add final range
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")
        
        return ", ".join(ranges)

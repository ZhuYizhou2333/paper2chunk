"""Data models for paper2chunk"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Block(BaseModel):
    """A block from MinerU parsing"""
    id: str = Field(description="Unique block ID")
    type: str = Field(description="Block type: text, header, table, image, equation, etc.")
    text: str = Field(default="", description="Text content of the block")
    level: Optional[int] = Field(default=None, description="Header level (1-4) if type is header")
    page: int = Field(description="Page number")
    bbox: Optional[List[float]] = Field(default=None, description="Bounding box [x0, y0, x1, y1]")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TreeNode(BaseModel):
    """A node in the document tree (AST)"""
    id: str = Field(description="Node ID")
    type: str = Field(description="Node type: root, section, content")
    title: Optional[str] = Field(default=None, description="Section title for section nodes")
    level: Optional[int] = Field(default=None, description="Section level")
    content: str = Field(default="", description="Content for content nodes")
    page_numbers: List[int] = Field(default_factory=list, description="Page numbers")
    children: List["TreeNode"] = Field(default_factory=list, description="Child nodes")
    
    def get_total_tokens(self) -> int:
        """Estimate total tokens in this node and its children"""
        # Rough estimation: 1 token ≈ 4 characters
        token_count = len(self.content) // 4
        for child in self.children:
            token_count += child.get_total_tokens()
        return token_count


class DocumentMetadata(BaseModel):
    """Metadata for a document"""
    title: str = Field(default="", description="Document title")
    author: Optional[str] = Field(default=None, description="Document author")
    publish_date: Optional[str] = Field(default=None, description="Publication date")
    source: Optional[str] = Field(default=None, description="Source of the document")
    language: str = Field(default="en", description="Document language")
    total_pages: int = Field(default=0, description="Total number of pages")
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


class ChunkMetadata(BaseModel):
    """Metadata for a chunk"""
    chunk_id: str = Field(description="Unique identifier for the chunk")
    document_title: str = Field(description="Title of the source document")
    section_hierarchy: List[str] = Field(default_factory=list, description="Section hierarchy (e.g., ['Chapter 1', 'Section 1.1'])")
    page_numbers: List[int] = Field(default_factory=list, description="Page numbers this chunk appears on")
    publish_date: Optional[str] = Field(default=None, description="Publication date")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Chunk creation timestamp")
    chunk_index: int = Field(description="Index of this chunk in the document")
    total_chunks: int = Field(description="Total number of chunks in the document")


class Chunk(BaseModel):
    """A semantic chunk of text"""
    content: str = Field(description="The actual content of the chunk")
    metadata: ChunkMetadata = Field(description="Metadata for this chunk")
    enhanced_content: Optional[str] = Field(default=None, description="LLM-enhanced content with semantic context")
    entities: List[str] = Field(default_factory=list, description="Extracted entities")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")


class Document(BaseModel):
    """A parsed document"""
    metadata: DocumentMetadata = Field(description="Document metadata")
    raw_text: str = Field(default="", description="Raw extracted text")
    blocks: List[Block] = Field(default_factory=list, description="Parsed blocks from MinerU")
    tree: Optional[TreeNode] = Field(default=None, description="Document tree (AST)")
    structured_content: List[Dict[str, Any]] = Field(default_factory=list, description="Structured content with sections (legacy)")
    images: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted images and charts")
    chunks: List[Chunk] = Field(default_factory=list, description="Generated chunks")


class Section(BaseModel):
    """A section in the document"""
    title: str = Field(description="Section title")
    level: int = Field(description="Section level (1=chapter, 2=section, etc.)")
    content: str = Field(description="Section content")
    page_numbers: List[int] = Field(default_factory=list, description="Page numbers")
    subsections: List["Section"] = Field(default_factory=list, description="Subsections")


# Update forward references
Section.model_rebuild()
TreeNode.model_rebuild()

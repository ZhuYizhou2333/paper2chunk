"""
paper2chunk: Convert PDF documents into RAG-friendly semantic chunks

This package provides tools to:
- Parse PDF documents
- Rewrite content with LLM for semantic enhancement
- Perform semantic chunking based on document structure
- Inject metadata into chunks
- Convert charts to text (optional)
- Output in RAG-friendly formats (LightRAG, LangChain)
"""

__version__ = "0.1.0"
__author__ = "ZhuYizhou"

from paper2chunk.core.pdf_parser import PDFParser
from paper2chunk.core.llm_rewriter import LLMRewriter
from paper2chunk.core.semantic_chunker import SemanticChunker
from paper2chunk.core.metadata_injector import MetadataInjector
from paper2chunk.core.chart_analyzer import ChartAnalyzer
from paper2chunk.pipeline import Paper2ChunkPipeline

__all__ = [
    "PDFParser",
    "LLMRewriter",
    "SemanticChunker",
    "MetadataInjector",
    "ChartAnalyzer",
    "Paper2ChunkPipeline",
]

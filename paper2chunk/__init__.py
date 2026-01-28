"""
paper2chunk: Convert PDF documents into RAG-friendly semantic chunks

This package provides tools to:
- Parse PDF documents using MinerU (Magic-PDF) API
- Repair TOC hierarchy with LLM
- Build document AST (Abstract Syntax Tree)
- Perform dual-threshold recursive DFS chunking
- Inject metadata into chunks
- Convert charts to text (optional)
- Output in RAG-friendly formats (LightRAG, LangChain)

Two pipelines available:
- Paper2ChunkPipeline: Main 4-layer architecture (MinerU-based)
- Paper2ChunkLegacyPipeline: Legacy pipeline using PyMuPDF (backward compatibility)
"""

__version__ = "0.1.0"
__author__ = "ZhuYizhou"

from paper2chunk.core.pdf_parser import PDFParser
from paper2chunk.core.pdf_parser_new import MinerUParser
from paper2chunk.core.logic_repair import LogicRepairer
from paper2chunk.core.tree_builder import TreeBuilder
from paper2chunk.core.semantic_chunker_new import DualThresholdChunker
from paper2chunk.core.llm_rewriter import LLMRewriter
from paper2chunk.core.semantic_chunker import SemanticChunker
from paper2chunk.core.metadata_injector import MetadataInjector
from paper2chunk.core.chart_analyzer import ChartAnalyzer
from paper2chunk.pipeline import Paper2ChunkPipeline
from paper2chunk.pipeline_legacy import Paper2ChunkLegacyPipeline

__all__ = [
    "PDFParser",
    "MinerUParser",
    "LogicRepairer",
    "TreeBuilder",
    "DualThresholdChunker",
    "LLMRewriter",
    "SemanticChunker",
    "MetadataInjector",
    "ChartAnalyzer",
    "Paper2ChunkPipeline",
    "Paper2ChunkLegacyPipeline",
]

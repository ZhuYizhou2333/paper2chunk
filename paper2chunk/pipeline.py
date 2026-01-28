"""Main pipeline using the 4-layer architecture"""

from typing import Optional, List
from pathlib import Path
from paper2chunk.config import Config
from paper2chunk.core import (
    MinerUParser,
    LogicRepairer,
    TreeBuilder,
    DualThresholdChunker,
    LLMRewriter,
    MetadataInjector,
    ChartAnalyzer,
)
from paper2chunk.models import Document, Chunk
from paper2chunk.output_formatters import (
    LightRAGFormatter,
    LangChainFormatter,
    MarkdownFormatter,
    JSONFormatter,
)


class Paper2ChunkPipeline:
    """Main pipeline using 4-layer architecture:
    
    1. Parsing Layer (MinerU): Visual extraction with layout analysis
    2. Logic Layer (LLM): TOC hierarchy repair
    3. Modeling Layer (Tree Builder): AST construction
    4. Slicing Layer (Dual-threshold DFS): RAG chunk generation
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the pipeline
        
        Args:
            config: Configuration object. If None, loads from environment.
            
        Raises:
            ValueError: If required configuration is missing
        """
        self.config = config or Config.from_env()
        
        # Validate required configuration
        if not self.config.mineru.api_key:
            raise ValueError(
                "MinerU API key is required.\n"
                "Please set MINERU_API_KEY in your .env file or environment.\n"
                "Get your API key from: https://mineru.net/"
            )
        
        if not (self.config.llm.openai_api_key or self.config.llm.anthropic_api_key):
            raise ValueError(
                "LLM API key is required for the pipeline.\n"
                "Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in your .env file."
            )
        
        # Initialize components
        try:
            # Layer 1: Parsing (MinerU)
            self.parser = MinerUParser(self.config.mineru)
            
            # Layer 2: Logic Repair (LLM)
            self.logic_repairer = LogicRepairer(self.config.llm)
            
            # Layer 3: Tree Builder
            self.tree_builder = TreeBuilder()
            
            # Layer 4: Dual-threshold Chunker
            self.chunker = DualThresholdChunker(
                self.config.chunking,
                self.config.llm if self.config.features.enable_semantic_enhancement else None
            )
            
            # Optional: Metadata Injector
            self.metadata_injector = MetadataInjector()
            
            # Optional: LLM Rewriter for semantic enhancement
            self.llm_rewriter = None
            if self.config.features.enable_semantic_enhancement:
                try:
                    self.llm_rewriter = LLMRewriter(self.config.llm)
                except Exception as e:
                    print(f"Warning: Could not initialize LLM rewriter: {e}")
            
            # Optional: Chart Analyzer
            self.chart_analyzer = None
            if self.config.features.enable_chart_to_text:
                try:
                    self.chart_analyzer = ChartAnalyzer(self.config.llm)
                except Exception as e:
                    print(f"Warning: Could not initialize chart analyzer: {e}")
                    
        except Exception as e:
            raise RuntimeError(f"Failed to initialize pipeline: {e}")
    
    def process(self, pdf_path: str) -> Document:
        """Process a PDF file through the 4-layer pipeline
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Processed document with chunks
        """
        print(f"\n{'='*60}")
        print(f"Processing PDF with 4-Layer Architecture")
        print(f"{'='*60}\n")
        print(f"Input: {pdf_path}\n")
        
        # Layer 1: Parsing (MinerU)
        print("【Layer 1/4】Parsing Layer - MinerU Visual Extraction")
        document = self.parser.parse(pdf_path)
        print(f"  ✓ Extracted {len(document.blocks)} blocks")
        print(f"  ✓ Document: {document.metadata.title}")
        print(f"  ✓ Pages: {document.metadata.total_pages}\n")
        
        # Layer 2: Logic Repair (LLM)
        print("【Layer 2/4】Logic Layer - LLM TOC Hierarchy Repair")
        document.blocks = self.logic_repairer.repair_hierarchy(document.blocks)
        print()
        
        # Layer 3: Tree Building (AST)
        print("【Layer 3/4】Modeling Layer - AST Construction")
        document.tree = self.tree_builder.build_tree(document.blocks)
        print()
        
        # Layer 4: Slicing (Dual-threshold DFS)
        print("【Layer 4/4】Slicing Layer - Dual-Threshold Recursive DFS")
        chunks = self.chunker.chunk_tree(
            document.tree,
            document.metadata.title,
            document.metadata.publish_date
        )
        print()
        
        # Optional: Inject metadata
        if self.config.features.enable_metadata_injection:
            print("【Optional】Injecting metadata into chunks...")
            chunks = self.metadata_injector.inject_metadata(chunks)
            print(f"  ✓ Metadata injected\n")
        
        # Optional: LLM enhancement
        if self.llm_rewriter and self.config.features.enable_semantic_enhancement:
            print("【Optional】Enhancing chunks with LLM...")
            chunks = self._enhance_chunks(chunks, document.metadata.title)
            print()
        
        # Optional: Chart analysis
        if self.chart_analyzer and self.config.features.enable_chart_to_text:
            print("【Optional】Analyzing charts and images...")
            chart_descriptions = self.chart_analyzer.analyze_images_in_document(
                document.images,
                document.metadata.title
            )
            print(f"  ✓ Analyzed {len(chart_descriptions)} images\n")
        
        # Update document with chunks
        document.chunks = chunks
        
        print(f"{'='*60}")
        print(f"✅ Processing Complete!")
        print(f"{'='*60}")
        print(f"Generated {len(chunks)} semantic chunks")
        if chunks:
            avg_size = sum(len(c.content) for c in chunks) // len(chunks)
            print(f"Average chunk size: {avg_size} characters")
        print(f"{'='*60}\n")
        
        return document
    
    def _enhance_chunks(self, chunks: List[Chunk], document_title: str) -> List[Chunk]:
        """Enhance chunks with LLM
        
        Args:
            chunks: List of chunks
            document_title: Document title
            
        Returns:
            Enhanced chunks
        """
        enhanced_chunks = []
        
        for i, chunk in enumerate(chunks):
            print(f"  Enhancing chunk {i+1}/{len(chunks)}...", end="\r")
            
            # Enhance content
            if not chunk.enhanced_content:
                enhanced_content = self.llm_rewriter.enhance_chunk(
                    chunk,
                    document_title,
                    chunk.metadata.section_hierarchy
                )
                chunk.enhanced_content = enhanced_content
            
            # Extract entities and keywords
            if not chunk.entities and not chunk.keywords:
                content_to_analyze = chunk.enhanced_content or chunk.content
                entities, keywords = self.llm_rewriter.extract_entities_and_keywords(
                    content_to_analyze
                )
                chunk.entities = entities
                chunk.keywords = keywords
            
            enhanced_chunks.append(chunk)
        
        print(f"  ✓ Enhanced {len(chunks)} chunks" + " " * 20)
        return enhanced_chunks
    
    def save_output(
        self,
        document: Document,
        output_path: str,
        format: str = "lightrag"
    ):
        """Save processed chunks to file
        
        Args:
            document: Processed document with chunks
            output_path: Path to save output
            format: Output format (lightrag, langchain, markdown, json)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        formatters = {
            "lightrag": LightRAGFormatter(),
            "langchain": LangChainFormatter(),
            "markdown": MarkdownFormatter(),
            "json": JSONFormatter(),
        }
        
        formatter = formatters.get(format.lower())
        if not formatter:
            raise ValueError(f"Unsupported format: {format}")
        
        print(f"Saving output to {output_path} (format: {format})...")
        
        if format == "markdown":
            formatter.to_file(document.chunks, str(output_path))
        else:
            formatter.to_json(document.chunks, str(output_path))
        
        print(f"✅ Output saved successfully!\n")

"""Main pipeline for paper2chunk"""

from typing import Optional, List
from pathlib import Path
from paper2chunk.config import Config
from paper2chunk.core import (
    PDFParser,
    LLMRewriter,
    SemanticChunker,
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
    """Main pipeline for converting PDFs to RAG-friendly chunks"""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the pipeline
        
        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config or Config.from_env()
        
        # Initialize components
        self.pdf_parser = PDFParser()
        self.semantic_chunker = SemanticChunker(self.config.chunking)
        self.metadata_injector = MetadataInjector()
        
        # Initialize LLM-dependent components only if needed
        self.llm_rewriter = None
        self.chart_analyzer = None
        
        if self.config.features.enable_semantic_enhancement:
            try:
                self.llm_rewriter = LLMRewriter(self.config.llm)
            except Exception as e:
                print(f"Warning: Could not initialize LLM rewriter: {e}")
                print("Semantic enhancement will be disabled.")
        
        if self.config.features.enable_chart_to_text:
            try:
                self.chart_analyzer = ChartAnalyzer(self.config.llm)
            except Exception as e:
                print(f"Warning: Could not initialize chart analyzer: {e}")
                print("Chart-to-text conversion will be disabled.")
    
    def process(self, pdf_path: str) -> Document:
        """Process a PDF file through the complete pipeline
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Processed document with chunks
        """
        print(f"Processing PDF: {pdf_path}")
        
        # Step 1: Parse PDF
        print("Step 1/5: Parsing PDF...")
        document = self.pdf_parser.parse(pdf_path)
        print(f"  ✓ Extracted {len(document.raw_text)} characters from {document.metadata.total_pages} pages")
        
        # Step 2: Analyze charts (optional)
        if self.chart_analyzer and self.config.features.enable_chart_to_text:
            print("Step 2/5: Analyzing charts and images...")
            chart_descriptions = self.chart_analyzer.analyze_images_in_document(
                document.images,
                document.metadata.title
            )
            print(f"  ✓ Analyzed {len(chart_descriptions)} images")
        else:
            print("Step 2/5: Skipping chart analysis (disabled or unavailable)")
        
        # Step 3: Semantic chunking
        print("Step 3/5: Creating semantic chunks...")
        chunks = self.semantic_chunker.chunk_document(document)
        print(f"  ✓ Created {len(chunks)} semantic chunks")
        
        # Step 4: Inject metadata
        if self.config.features.enable_metadata_injection:
            print("Step 4/5: Injecting metadata...")
            chunks = self.metadata_injector.inject_metadata(chunks)
            print(f"  ✓ Metadata injected into all chunks")
        else:
            print("Step 4/5: Skipping metadata injection (disabled)")
        
        # Step 5: LLM enhancement (optional)
        if self.llm_rewriter and self.config.features.enable_semantic_enhancement:
            print("Step 5/5: Enhancing chunks with LLM...")
            chunks = self._enhance_chunks(chunks, document.metadata.title)
            print(f"  ✓ Enhanced all chunks with semantic context")
        else:
            print("Step 5/5: Skipping LLM enhancement (disabled or unavailable)")
        
        # Update document with chunks
        document.chunks = chunks
        
        print(f"\n✅ Processing complete! Generated {len(chunks)} chunks.")
        return document
    
    def _enhance_chunks(self, chunks: List[Chunk], document_title: str) -> List[Chunk]:
        """Enhance chunks with LLM"""
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
        
        print()  # New line after progress
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
        
        print(f"\nSaving output to {output_path} (format: {format})...")
        
        if format == "markdown":
            formatter.to_file(document.chunks, str(output_path))
        else:
            formatter.to_json(document.chunks, str(output_path))
        
        print(f"✅ Output saved successfully!")

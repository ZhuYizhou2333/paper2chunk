"""Command-line interface for paper2chunk"""

import argparse
import sys
from pathlib import Path
from paper2chunk.pipeline import Paper2ChunkPipeline
from paper2chunk.pipeline_sota import Paper2ChunkSOTAPipeline
from paper2chunk.config import Config


def main():
    """Main entry point for CLI"""
    parser = argparse.ArgumentParser(
        description="paper2chunk: Convert PDF documents into RAG-friendly semantic chunks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use new SOTA pipeline (recommended)
  paper2chunk input.pdf -o output.json --sota
  
  # Use legacy pipeline
  paper2chunk input.pdf -o output.json
  
  # Specify output format
  paper2chunk input.pdf -o output.json --format lightrag --sota
  
  # Disable LLM enhancement
  paper2chunk input.pdf -o output.json --no-enhancement
  
  # Disable chart analysis
  paper2chunk input.pdf -o output.json --no-charts
  
Supported formats: lightrag, langchain, markdown, json

Pipelines:
  --sota: New 4-layer SOTA architecture (MinerU + LLM hierarchy repair + AST + dual-threshold DFS)
  default: Legacy pipeline (PyMuPDF + simple chunking)
        """
    )
    
    parser.add_argument(
        "input",
        type=str,
        help="Path to input PDF file"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="Path to output file"
    )
    
    parser.add_argument(
        "-f", "--format",
        type=str,
        default="lightrag",
        choices=["lightrag", "langchain", "markdown", "json"],
        help="Output format (default: lightrag)"
    )
    
    parser.add_argument(
        "--sota",
        action="store_true",
        help="Use new SOTA 4-layer pipeline (MinerU + LLM + AST + DFS)"
    )
    
    parser.add_argument(
        "--no-enhancement",
        action="store_true",
        help="Disable LLM-based semantic enhancement"
    )
    
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Disable chart-to-text conversion"
    )
    
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Disable metadata injection"
    )
    
    parser.add_argument(
        "--soft-limit",
        type=int,
        help="Soft limit for chunk size in tokens (SOTA pipeline only)"
    )
    
    parser.add_argument(
        "--hard-limit",
        type=int,
        help="Hard limit for chunk size in tokens (SOTA pipeline only)"
    )
    
    # Legacy pipeline options
    parser.add_argument(
        "--max-chunk-size",
        type=int,
        help="Maximum chunk size in characters (legacy pipeline only)"
    )
    
    parser.add_argument(
        "--min-chunk-size",
        type=int,
        help="Minimum chunk size in characters (legacy pipeline only)"
    )
    
    parser.add_argument(
        "--overlap",
        type=int,
        help="Overlap size between chunks (legacy pipeline only)"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)
    
    if not input_path.suffix.lower() == ".pdf":
        print(f"Error: Input file must be a PDF")
        sys.exit(1)
    
    # Load configuration
    config = Config.from_env()
    
    # Override with command-line arguments
    if args.no_enhancement:
        config.features.enable_semantic_enhancement = False
    
    if args.no_charts:
        config.features.enable_chart_to_text = False
    
    if args.no_metadata:
        config.features.enable_metadata_injection = False
    
    # SOTA pipeline options
    if args.soft_limit:
        config.chunking.soft_limit = args.soft_limit
    
    if args.hard_limit:
        config.chunking.hard_limit = args.hard_limit
    
    # Legacy pipeline options
    if args.max_chunk_size:
        # For backward compatibility, map to chunking config
        # This will only work with legacy pipeline
        pass
    
    if args.min_chunk_size:
        pass
    
    if args.overlap:
        pass
    
    # Run pipeline
    try:
        print("=" * 60)
        print("paper2chunk - PDF to RAG-friendly chunks")
        print("=" * 60)
        print()
        
        if args.sota:
            print("Using: SOTA 4-Layer Pipeline")
            print("  1. MinerU Visual Extraction")
            print("  2. LLM TOC Hierarchy Repair")
            print("  3. AST Construction")
            print("  4. Dual-Threshold DFS Chunking")
            print()
            pipeline = Paper2ChunkSOTAPipeline(config)
        else:
            print("Using: Legacy Pipeline")
            print()
            pipeline = Paper2ChunkPipeline(config)
        
        document = pipeline.process(str(input_path))
        pipeline.save_output(document, args.output, args.format)
        
        print()
        print("=" * 60)
        print("Summary:")
        print(f"  Input: {args.input}")
        print(f"  Output: {args.output}")
        print(f"  Format: {args.format}")
        print(f"  Total chunks: {len(document.chunks)}")
        print(f"  Total pages: {document.metadata.total_pages}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Command-line interface for paper2chunk"""

import argparse
import sys
from pathlib import Path
from paper2chunk.pipeline import Paper2ChunkPipeline
from paper2chunk.config import Config


def main():
    """Main entry point for CLI"""
    parser = argparse.ArgumentParser(
        description="paper2chunk: Convert PDF documents into RAG-friendly semantic chunks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  paper2chunk input.pdf -o output.json
  
  # Specify output format
  paper2chunk input.pdf -o output.json --format lightrag
  
  # Disable LLM enhancement
  paper2chunk input.pdf -o output.json --no-enhancement
  
  # Disable chart analysis
  paper2chunk input.pdf -o output.json --no-charts
  
Supported formats: lightrag, langchain, markdown, json
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
        "--max-chunk-size",
        type=int,
        help="Maximum chunk size in characters"
    )
    
    parser.add_argument(
        "--min-chunk-size",
        type=int,
        help="Minimum chunk size in characters"
    )
    
    parser.add_argument(
        "--overlap",
        type=int,
        help="Overlap size between chunks"
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
    
    if args.max_chunk_size:
        config.chunking.max_chunk_size = args.max_chunk_size
    
    if args.min_chunk_size:
        config.chunking.min_chunk_size = args.min_chunk_size
    
    if args.overlap:
        config.chunking.overlap_size = args.overlap
    
    # Run pipeline
    try:
        print("=" * 60)
        print("paper2chunk - PDF to RAG-friendly chunks")
        print("=" * 60)
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

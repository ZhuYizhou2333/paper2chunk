"""Example usage of paper2chunk"""

from paper2chunk import Paper2ChunkPipeline
from paper2chunk.config import Config

def example_basic_usage():
    """Basic usage example"""
    # Initialize pipeline with default configuration
    pipeline = Paper2ChunkPipeline()
    
    # Process a PDF
    document = pipeline.process("example.pdf")
    
    # Save output in different formats
    pipeline.save_output(document, "output_lightrag.json", format="lightrag")
    pipeline.save_output(document, "output_langchain.json", format="langchain")
    pipeline.save_output(document, "output.md", format="markdown")
    
    print(f"Generated {len(document.chunks)} chunks")


def example_custom_config():
    """Example with custom configuration"""
    # Create custom configuration
    config = Config.from_env()
    
    # Customize chunking parameters
    config.chunking.max_chunk_size = 1500
    config.chunking.min_chunk_size = 200
    config.chunking.overlap_size = 100
    
    # Disable optional features
    config.features.enable_chart_to_text = False
    
    # Initialize pipeline with custom config
    pipeline = Paper2ChunkPipeline(config)
    
    # Process PDF
    document = pipeline.process("example.pdf")
    
    # Save output
    pipeline.save_output(document, "output.json", format="lightrag")


def example_programmatic_access():
    """Example of accessing chunk data programmatically"""
    pipeline = Paper2ChunkPipeline()
    document = pipeline.process("example.pdf")
    
    # Access chunks
    for i, chunk in enumerate(document.chunks):
        print(f"\nChunk {i + 1}:")
        print(f"  Content length: {len(chunk.content)} characters")
        print(f"  Section: {' > '.join(chunk.metadata.section_hierarchy)}")
        print(f"  Pages: {chunk.metadata.page_numbers}")
        print(f"  Entities: {chunk.entities}")
        print(f"  Keywords: {chunk.keywords}")


if __name__ == "__main__":
    print("paper2chunk Examples")
    print("=" * 60)
    print("\n1. Basic usage:")
    print("   from paper2chunk import Paper2ChunkPipeline")
    print("   pipeline = Paper2ChunkPipeline()")
    print("   document = pipeline.process('example.pdf')")
    print("   pipeline.save_output(document, 'output.json', 'lightrag')")
    print("\n2. Custom configuration:")
    print("   See example_custom_config() function")
    print("\n3. Programmatic access:")
    print("   See example_programmatic_access() function")

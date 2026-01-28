"""
Example script demonstrating the 4-layer pipeline

This example shows how to use the Paper2ChunkPipeline which implements:
1. MinerU Visual Extraction (parsing layer)
2. LLM TOC Hierarchy Repair (logic layer)
3. AST Construction (modeling layer)
4. Dual-Threshold DFS Chunking (slicing layer)
"""

from paper2chunk import Paper2ChunkPipeline
from paper2chunk.config import Config

def main():
    """Run pipeline example"""
    
    # Check if example PDF exists
    import os
    pdf_path = "example.pdf"  # Replace with your PDF path
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF file not found: {pdf_path}")
        print("\nTo run this example:")
        print("1. Set MINERU_API_KEY in .env file (get from https://mineru.net/)")
        print("2. Set OPENAI_API_KEY (and optional OPENAI_BASE_URL) in .env file")
        print("3. Replace 'example.pdf' with path to your PDF file")
        print("\nExample:")
        print("  python pipeline_example.py")
        return
    
    # Load configuration from environment
    config = Config.from_env()
    
    # Optional: Customize configuration
    config.chunking.soft_limit = 800  # Optimal chunk size in tokens
    config.chunking.hard_limit = 2000  # Maximum chunk size in tokens
    config.features.enable_semantic_enhancement = True
    config.features.enable_metadata_injection = True
    
    try:
        # Initialize pipeline (will validate API keys)
        pipeline = Paper2ChunkPipeline(config)
        print("Starting pipeline processing...")
        print()
        
        # Process the document
        document = pipeline.process(pdf_path)
        
        # Save output in different formats
        pipeline.save_output(document, "output_lightrag.json", format="lightrag")
        pipeline.save_output(document, "output_langchain.json", format="langchain")
        pipeline.save_output(document, "output.md", format="markdown")
        
        # Access chunks programmatically
        print("\nFirst 3 chunks:")
        for i, chunk in enumerate(document.chunks[:3]):
            print(f"\n--- Chunk {i+1} ---")
            print(f"Section: {' → '.join(chunk.metadata.section_hierarchy)}")
            print(f"Pages: {chunk.metadata.page_numbers}")
            print(f"Content: {chunk.content[:200]}...")
            if chunk.entities:
                print(f"Entities: {chunk.entities[:5]}")
            if chunk.keywords:
                print(f"Keywords: {chunk.keywords[:5]}")
        
        print("\n✅ Example completed successfully!")
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

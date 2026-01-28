# Quick Start Guide

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ZhuYizhou2333/paper2chunk.git
cd paper2chunk
```

2. Install dependencies:
```bash
pip install -r requirements.txt
# or
pip install -e .
```

3. Set up API keys (optional, required for LLM features):
```bash
cp .env.example .env
# Edit .env and add your OpenAI or Anthropic API key
```

## Basic Usage

### Command Line

```bash
# Process a PDF without LLM enhancement (no API key needed)
paper2chunk input.pdf -o output.json --no-enhancement

# Process with LLM enhancement (requires API key)
paper2chunk input.pdf -o output.json

# Different output formats
paper2chunk input.pdf -o output.md --format markdown
paper2chunk input.pdf -o output.json --format langchain

# Custom chunk sizes
paper2chunk input.pdf -o output.json --max-chunk-size 1500 --overlap 100
```

### Python API

```python
from paper2chunk import Paper2ChunkPipeline
from paper2chunk.config import Config

# Basic usage without LLM (no API key needed)
config = Config.from_env()
config.features.enable_semantic_enhancement = False
config.features.enable_chart_to_text = False

pipeline = Paper2ChunkPipeline(config)
document = pipeline.process("example.pdf")
pipeline.save_output(document, "output.json", format="lightrag")

# Access the chunks
for chunk in document.chunks:
    print(f"Chunk {chunk.metadata.chunk_index + 1}:")
    print(f"  Section: {' → '.join(chunk.metadata.section_hierarchy)}")
    print(f"  Pages: {chunk.metadata.page_numbers}")
    print(f"  Content length: {len(chunk.content)} chars")
```

### With LLM Enhancement

```python
from paper2chunk import Paper2ChunkPipeline

# Make sure you have OPENAI_API_KEY in .env
pipeline = Paper2ChunkPipeline()  # Loads config from .env
document = pipeline.process("example.pdf")
pipeline.save_output(document, "output.json")

# Enhanced chunks will have semantic context and entities
for chunk in document.chunks:
    print(f"Enhanced: {chunk.enhanced_content[:100]}...")
    print(f"Entities: {chunk.entities}")
    print(f"Keywords: {chunk.keywords}")
```

## Features

### 1. Semantic Chunking (Always Enabled)
Splits documents based on natural structure (chapters, sections, paragraphs).

### 2. Metadata Injection (Can be Disabled)
Adds document title, section hierarchy, dates, and page numbers to each chunk.

### 3. LLM Enhancement (Optional - Requires API Key)
- Resolves pronouns and references
- Adds semantic context
- Extracts entities and keywords

### 4. Chart Analysis (Optional - Requires API Key)
Converts charts and images to text descriptions.

## Output Formats

### LightRAG (Default)
Optimized for Graph RAG systems with entities and relationships.

### LangChain
Compatible with LangChain Document format.

### Markdown
Human-readable format with metadata headers.

### JSON
Standard JSON format for custom processing.

## Configuration

### Environment Variables (.env)
```bash
# LLM Provider
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4

# Chunking
MAX_CHUNK_SIZE=1000
MIN_CHUNK_SIZE=100
OVERLAP_SIZE=50

# Features
ENABLE_CHART_TO_TEXT=true
ENABLE_SEMANTIC_ENHANCEMENT=true
```

### Programmatic Configuration
```python
from paper2chunk.config import Config

config = Config.from_env()

# Customize chunking
config.chunking.max_chunk_size = 1500
config.chunking.min_chunk_size = 200

# Disable features
config.features.enable_semantic_enhancement = False
config.features.enable_chart_to_text = False
```

## Troubleshooting

### No API Key
If you don't have an API key, disable LLM features:
```bash
paper2chunk input.pdf -o output.json --no-enhancement --no-charts
```

### Import Errors
Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Memory Issues
For large PDFs, increase chunk size or reduce overlap:
```bash
paper2chunk input.pdf -o output.json --max-chunk-size 2000 --overlap 0
```

## Examples

See the [examples](examples/) directory for more usage examples.

## Documentation

- [API Documentation](docs/API.md)
- [Contributing Guide](CONTRIBUTING.md)

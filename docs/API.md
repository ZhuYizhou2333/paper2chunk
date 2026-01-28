# paper2chunk API Documentation

## Core Classes

### Paper2ChunkPipeline

Main pipeline for processing PDF documents.

```python
from paper2chunk import Paper2ChunkPipeline

pipeline = Paper2ChunkPipeline(config=None)
```

**Methods:**

- `process(pdf_path: str) -> Document`: Process a PDF file
- `save_output(document: Document, output_path: str, format: str)`: Save output

### Config

Configuration management.

```python
from paper2chunk.config import Config

config = Config.from_env()
```

**Attributes:**

- `llm`: LLM configuration
- `chunking`: Chunking parameters
- `features`: Feature flags

### PDFParser

Parse PDF documents.

```python
from paper2chunk.core import PDFParser

parser = PDFParser()
document = parser.parse("example.pdf")
```

### SemanticChunker

Chunk documents semantically.

```python
from paper2chunk.core import SemanticChunker
from paper2chunk.config import ChunkingConfig

config = ChunkingConfig(max_chunk_size=1000)
chunker = SemanticChunker(config)
chunks = chunker.chunk_document(document)
```

### MetadataInjector

Inject metadata into chunks.

```python
from paper2chunk.core import MetadataInjector

injector = MetadataInjector()
enhanced_chunks = injector.inject_metadata(chunks)
```

### LLMRewriter

Enhance chunks with LLM.

```python
from paper2chunk.core import LLMRewriter
from paper2chunk.config import LLMConfig

config = LLMConfig(provider="openai", openai_api_key="...")
rewriter = LLMRewriter(config)
enhanced_content = rewriter.enhance_chunk(chunk, title, hierarchy)
```

## Models

### Document

```python
from paper2chunk.models import Document

document = Document(
    metadata=DocumentMetadata(...),
    raw_text="...",
    structured_content=[...],
    images=[...],
    chunks=[...]
)
```

### Chunk

```python
from paper2chunk.models import Chunk, ChunkMetadata

chunk = Chunk(
    content="...",
    metadata=ChunkMetadata(...),
    enhanced_content="...",
    entities=[...],
    keywords=[...]
)
```

## Output Formatters

### LightRAGFormatter

```python
from paper2chunk.output_formatters import LightRAGFormatter

formatter = LightRAGFormatter()
formatted = formatter.format(chunks)
formatter.to_json(chunks, "output.json")
```

### LangChainFormatter

```python
from paper2chunk.output_formatters import LangChainFormatter

formatter = LangChainFormatter()
formatted = formatter.format(chunks)
```

### MarkdownFormatter

```python
from paper2chunk.output_formatters import MarkdownFormatter

formatter = MarkdownFormatter()
markdown = formatter.format(chunks)
formatter.to_file(chunks, "output.md")
```

## Configuration Options

### Chunking Configuration

```python
from paper2chunk.config import ChunkingConfig

config = ChunkingConfig(
    max_chunk_size=1000,      # Maximum chunk size
    min_chunk_size=100,       # Minimum chunk size
    overlap_size=50,          # Overlap between chunks
    preserve_structure=True   # Preserve document structure
)
```

### LLM Configuration

```python
from paper2chunk.config import LLMConfig

config = LLMConfig(
    provider="openai",
    openai_api_key="...",
    openai_model="gpt-4",
    temperature=0.3,
    max_tokens=4000
)
```

### Feature Configuration

```python
from paper2chunk.config import FeatureConfig

config = FeatureConfig(
    enable_chart_to_text=True,
    enable_semantic_enhancement=True,
    enable_metadata_injection=True
)
```

## CLI Usage

```bash
paper2chunk [OPTIONS] input.pdf

Options:
  -o, --output PATH          Output file path (required)
  -f, --format FORMAT        Output format [lightrag|langchain|markdown|json]
  --no-enhancement          Disable LLM enhancement
  --no-charts               Disable chart analysis
  --no-metadata             Disable metadata injection
  --max-chunk-size INT      Maximum chunk size
  --min-chunk-size INT      Minimum chunk size
  --overlap INT             Overlap size
  --help                    Show help message
```

## Examples

See the [examples](../examples/usage_examples.py) directory for more usage examples.

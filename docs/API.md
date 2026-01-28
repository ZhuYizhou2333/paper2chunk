# paper2chunk API 参考

本文档提供 `paper2chunk` 的核心类、配置与命令行参数的快速参考。更完整的架构说明见 `docs/ARCHITECTURE.md`。

## 核心入口

### `Paper2ChunkPipeline`（默认管道：4 层架构）

```python
from paper2chunk import Paper2ChunkPipeline

pipeline = Paper2ChunkPipeline()  # 默认从环境变量/.env 加载配置
document = pipeline.process("example.pdf")
pipeline.save_output(document, "output.json", format="lightrag")
```

说明：
- 默认管道依赖 MinerU 与 LLM（需要 `MINERU_API_KEY` 与 `OPENAI_API_KEY`）

### `Paper2ChunkLegacyPipeline`（传统管道）

```python
from paper2chunk import Paper2ChunkLegacyPipeline
from paper2chunk.config import Config

config = Config.from_env()
config.features.enable_semantic_enhancement = False
config.features.enable_chart_to_text = False

pipeline = Paper2ChunkLegacyPipeline(config)
document = pipeline.process("example.pdf")
pipeline.save_output(document, "output.json", format="json")
```

## 配置（`paper2chunk/config.py`）

```python
from paper2chunk.config import Config

config = Config.from_env()
```

常用环境变量（节选）：
```bash
# MinerU（默认管道必需）
MINERU_API_KEY=...
MINERU_TIMEOUT=300
MINERU_POLL_INTERVAL=5
MINERU_MAX_POLL_ATTEMPTS=60

# LLM（默认管道必需；传统管道可关闭相关功能）
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选：自定义 OpenAI 兼容端点
OPENAI_MODEL=gpt-4o

# 默认管道分片（token）
CHUNK_SOFT_LIMIT=800
CHUNK_HARD_LIMIT=2000
```

## 输出格式化器

位于 `paper2chunk/output_formatters/formatters.py`：
- `LightRAGFormatter`
- `LangChainFormatter`
- `MarkdownFormatter`
- `JSONFormatter`

## 命令行（CLI）

安装后会提供 `paper2chunk` 命令：

```bash
paper2chunk [OPTIONS] input.pdf
```

常用参数（节选）：
- `-o/--output`：输出路径（必填）
- `-f/--format`：`lightrag|langchain|markdown|json`
- `--legacy`：启用传统管道（不走 MinerU）
- `--no-enhancement`：禁用 LLM 语义增强
- `--no-charts`：禁用图表分析
- `--no-metadata`：禁用元数据注入

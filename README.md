# paper2chunk 📄➡️🧩

> **将非结构化 PDF 转化为语义完整、结构清晰、元数据丰富的 RAG 友好分片**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

paper2chunk 是一个专为 RAG（检索增强生成）系统设计的 PDF 文档处理工具。它的核心目标是解决 RAG 系统中的**"碎片化语义丢失"**问题，将非结构化的 PDF 转化为**语义完整、结构清晰、元数据丰富**的原子化分片（Chunks）。

## 🆕 重大更新：SOTA 4层架构

本版本引入了基于**行业 SOTA 方法**的全新 4 层架构：

### 🏗️ SOTA 架构概览

整个处理流程是一个从"无序"到"有序"，从"物理视界"到"逻辑语义"的升维过程。

#### 1️⃣ 解析层 (The Parser): MinerU 的视觉提取
- **输入**: 原始 PDF (金融研报/论文)
- **工具**: MinerU (Magic-PDF) API
- **核心任务**: 版面分析 (Layout Analysis)
  - 精准划分：Text (正文), Header (标题), Table (表格), Image (图片), Equation (公式)
  - 自动去除页眉页脚等无关信息
- **关键产物**: JSON 结构化数据

#### 2️⃣ 逻辑层 (The Logic Repair): LLM 目录树修复
- **痛点**: MinerU 只能识别"这是标题"，但分不清是 H1 还是 H3
- **解决方案**: "骨架提取 + LLM 修复"
  - 提取所有 header 形成"疑似目录列表"
  - 发送给 LLM (GPT-4o) 进行层级标注
  - 回填正确的 Level 属性到原始 Block

#### 3️⃣ 建模层 (The Tree Builder): 构建抽象语法树 (AST)
- **核心任务**: 将线性 Block 列表"折叠"成嵌套的文档对象树
- **算法**: 基于栈的构建算法 (Stack-based Construction)
  - 遇到 Header: 弹出栈，挂载新节点，入栈
  - 遇到 Content: 直接挂载到栈顶节点

#### 4️⃣ 切片层 (The Slicer): 递归深度优先聚合
- **核心任务**: 生成 RAG 用的 Chunk
- **原则**: 结构边界 > 内容长度
- **算法**: 双阈值递归 DFS (Dual-Threshold Recursive DFS)
  - **Soft_Limit** (800 tokens): 最佳长度
  - **Hard_Limit** (2000 tokens): 最大长度
  - Base Case: < Soft_Limit → 保留完整结构
  - Recursive Case: > Soft_Limit → 递归处理
  - Edge Case: 叶子节点 > Hard_Limit → LLM 语义拆解

## 🎯 核心问题

传统的文档切片方法（如按字符数、句子数切分）会导致：
- ❌ 语义链条被切断
- ❌ 上下文信息丢失
- ❌ 代词引用不明确（"它"指的是什么？）
- ❌ 时间、地点等关键信息缺失

**paper2chunk 的解决方案：**
- ✅ 基于文档自然结构切分（章节、段落）
- ✅ LLM 语义增强（"它" → "**[动量因子]**"）
- ✅ 自动注入元数据（标题、日期、章节层级）
- ✅ 图表转文字描述（可选）
- ✅ 提取实体和关键词

## 📦 安装

### 使用 pip 安装
```bash
pip install -e .
```

### 安装依赖
```bash
pip install -r requirements.txt
```

### 环境配置
复制环境变量模板并配置：
```bash
cp .env.example .env
# 编辑 .env 文件，添加你的 API 密钥
```

**必需配置（SOTA 管道）：**
```bash
# MinerU API 配置（Magic-PDF）
MINERU_API_KEY=your_mineru_api_key_here
MINERU_API_URL=https://api.mineru.cn/v1/parse

# OpenAI 配置（推荐使用 GPT-4o）
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o

# 或 Anthropic 配置
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-opus-20240229

# 选择 LLM 提供商
LLM_PROVIDER=openai  # 或 anthropic

# 分片配置（token 数）
CHUNK_SOFT_LIMIT=800
CHUNK_HARD_LIMIT=2000
```

## 🚀 快速开始

### 命令行使用

#### 使用新 SOTA 管道（推荐）
```bash
# 基本用法
paper2chunk input.pdf -o output.json --sota

# 指定输出格式
paper2chunk input.pdf -o output.json --format lightrag --sota

# 输出为 Markdown
paper2chunk input.pdf -o output.md --format markdown --sota

# 禁用 LLM 增强（更快，但语义丰富度降低）
paper2chunk input.pdf -o output.json --no-enhancement --sota

# 自定义分片参数
paper2chunk input.pdf -o output.json --soft-limit 1000 --hard-limit 2500 --sota
```

#### 使用传统管道（向后兼容）
```bash
# 基本用法（使用 PyMuPDF）
paper2chunk input.pdf -o output.json

# 自定义参数
paper2chunk input.pdf -o output.json --max-chunk-size 1500 --overlap 100
```

### Python API 使用

#### SOTA 管道
```python
from paper2chunk import Paper2ChunkSOTAPipeline

# 初始化 SOTA 管道
pipeline = Paper2ChunkSOTAPipeline()

# 处理 PDF
document = pipeline.process("example.pdf")

# 保存输出
pipeline.save_output(document, "output.json", format="lightrag")

# 访问分片数据
for chunk in document.chunks:
    print(f"Content: {chunk.content}")
    print(f"Section: {chunk.metadata.section_hierarchy}")
    print(f"Entities: {chunk.entities}")
    print(f"Keywords: {chunk.keywords}")
```

#### 传统管道
```python
from paper2chunk import Paper2ChunkPipeline

# 初始化传统管道
pipeline = Paper2ChunkPipeline()

# 处理 PDF
document = pipeline.process("example.pdf")

# 保存输出
pipeline.save_output(document, "output.json", format="lightrag")
```

### 自定义配置

```python
from paper2chunk import Paper2ChunkSOTAPipeline
from paper2chunk.config import Config

# 加载并自定义配置
config = Config.from_env()
config.chunking.soft_limit = 1000  # 调整软限制
config.chunking.hard_limit = 2500  # 调整硬限制
config.features.enable_chart_to_text = False

# 使用自定义配置
pipeline = Paper2ChunkSOTAPipeline(config)
document = pipeline.process("example.pdf")
```

## 📊 输出示例

### LightRAG 格式输出

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "📄 **Document**: 量化投资研究报告\n📍 **Section**: 第三章 → 因子分析\n📅 **Date**: 2020-01-01\n📖 **Pages**: 15-17\n\n**[动量因子]** 在 **[2020年]** 表现很好，超额收益达到 **15%**...",
  "metadata": {
    "document_title": "量化投资研究报告",
    "section_hierarchy": ["第三章", "因子分析"],
    "page_numbers": [15, 16, 17],
    "publish_date": "2020-01-01"
  },
  "entities": ["动量因子", "2020年", "超额收益"],
  "keywords": ["量化投资", "因子分析", "动量", "收益"]
}
```

## 🏗️ 架构对比

### SOTA 管道（新）
```
PDF Input
    ↓
[MinerUParser] ──→ 视觉提取 + 版面分析
    ↓
[LogicRepairer] ──→ LLM 目录层级修复
    ↓
[TreeBuilder] ──→ AST 构建
    ↓
[DualThresholdChunker] ──→ 双阈值递归 DFS 切片
    ↓
[MetadataInjector] ──→ 注入元数据（可选）
    ↓
[LLMRewriter] ──→ 语义增强（可选）
    ↓
[OutputFormatter] ──→ 输出格式化
    ↓
RAG-ready Chunks
```

### 传统管道（向后兼容）
```
PDF Input
    ↓
[PDFParser] ──→ PyMuPDF 提取
    ↓
[SemanticChunker] ──→ 基于结构切分
    ↓
[MetadataInjector] ──→ 注入元数据
    ↓
[LLMRewriter] ──→ 语义增强（可选）
    ↓
[ChartAnalyzer] ──→ 图表分析（可选）
    ↓
[OutputFormatter] ──→ 输出格式化
    ↓
RAG-ready Chunks
```

## ⚙️ 配置选项

### SOTA 管道配置
- `soft_limit`: 软限制，最佳分片大小（token 数），默认 800
- `hard_limit`: 硬限制，最大分片大小（token 数），默认 2000
- `preserve_structure`: 保持文档结构，默认 true

### 传统管道配置
- `max_chunk_size`: 最大分片大小（字符数），默认 1000
- `min_chunk_size`: 最小分片大小（字符数），默认 100
- `overlap_size`: 重叠区域大小（字符数），默认 50

### 功能开关
- `enable_semantic_enhancement`: 启用 LLM 语义增强，默认 true
- `enable_chart_to_text`: 启用图表转文字，默认 true
- `enable_metadata_injection`: 启用元数据注入，默认 true

### LLM 配置
- `provider`: LLM 提供商（openai 或 anthropic）
- `openai_model`: OpenAI 模型名称，默认 gpt-4o
- `anthropic_model`: Anthropic 模型名称
- `temperature`: 温度参数，默认 0.3

## 🎓 使用场景

1. **学术论文处理**：将复杂的学术论文转化为易于检索的知识片段
2. **技术文档转换**：将技术文档转化为 RAG 系统可用的格式
3. **金融报告分析**：处理金融研究报告，保留关键数据和上下文
4. **法律文件处理**：保持法律文件的章节结构和引用关系
5. **知识库构建**：为企业知识库系统准备高质量的文档片段

## 🔬 SOTA 管道优势

### vs 传统方法
| 特性 | SOTA 管道 | 传统管道 | 简单切片 |
|-----|----------|---------|---------|
| 版面分析 | ✅ 视觉 AI | ⚠️ 启发式 | ❌ 无 |
| 层级识别 | ✅ LLM 修复 | ⚠️ 字体大小 | ❌ 无 |
| 结构保持 | ✅ AST | ⚠️ 部分 | ❌ 无 |
| 智能切片 | ✅ 双阈值 DFS | ⚠️ 简单规则 | ❌ 固定长度 |
| 语义完整性 | ✅ 高 | ⚠️ 中 | ❌ 低 |

### 关键创新点
1. **MinerU 集成**: 行业领先的 PDF 视觉解析能力
2. **LLM 层级修复**: 自动修正文档目录结构
3. **AST 建模**: 从线性到树状的升维处理
4. **双阈值 DFS**: 结构优先的智能切片算法
5. **LLM 手术刀**: 超大块的语义拆解

## 🤝 贡献

欢迎贡献代码、报告问题或提出新功能建议！

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 🙏 致谢

感谢以下开源项目：
- **MinerU (Magic-PDF)** - SOTA PDF 视觉解析
- **PyMuPDF** - 传统 PDF 解析
- **OpenAI / Anthropic** - LLM 支持
- **LangChain** - RAG 框架
- **LightRAG** - Graph RAG 实现

---

**Made with ❤️ for the RAG community**

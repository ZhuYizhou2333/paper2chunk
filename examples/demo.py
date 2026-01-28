#!/usr/bin/env python3
"""
Demo script showing paper2chunk functionality without requiring a real PDF or API keys.

This demonstrates the core chunking, metadata injection, and output formatting
capabilities using synthetic data.
"""

from paper2chunk.models import Document, DocumentMetadata, Chunk, ChunkMetadata
from paper2chunk.core import SemanticChunker, MetadataInjector
from paper2chunk.config import ChunkingConfig
from paper2chunk.output_formatters import (
    LightRAGFormatter,
    LangChainFormatter,
    MarkdownFormatter
)


def create_demo_document():
    """Create a synthetic document for demonstration"""
    
    # Create document metadata
    metadata = DocumentMetadata(
        title="量化投资研究报告：动量因子分析",
        author="量化研究团队",
        publish_date="2020-01-15",
        source="demo_paper.pdf",
        total_pages=3,
    )
    
    # Create structured content simulating a parsed PDF
    structured_content = [
        {
            "text": "量化投资研究报告",
            "page": 1,
            "font_size": 18.0,
            "is_heading": True,
            "level": 1,
        },
        {
            "text": "本报告分析了动量因子在中国A股市场的表现。",
            "page": 1,
            "font_size": 11.0,
            "is_heading": False,
            "level": 0,
        },
        {
            "text": "第一章 研究背景",
            "page": 1,
            "font_size": 14.0,
            "is_heading": True,
            "level": 2,
        },
        {
            "text": "动量效应是指股票的过去收益率能够预测未来收益率的现象。在学术界和实务界，它被广泛认为是一个重要的市场异象。",
            "page": 1,
            "font_size": 11.0,
            "is_heading": False,
            "level": 0,
        },
        {
            "text": "本研究着重分析了2015年至2020年期间，动量因子在中国A股市场的表现。",
            "page": 1,
            "font_size": 11.0,
            "is_heading": False,
            "level": 0,
        },
        {
            "text": "第二章 数据与方法",
            "page": 2,
            "font_size": 14.0,
            "is_heading": True,
            "level": 2,
        },
        {
            "text": "2.1 数据来源",
            "page": 2,
            "font_size": 12.0,
            "is_heading": True,
            "level": 3,
        },
        {
            "text": "本研究使用了沪深300成分股的日频交易数据。数据来源于Wind数据库，时间跨度为2015年1月1日至2020年12月31日。",
            "page": 2,
            "font_size": 11.0,
            "is_heading": False,
            "level": 0,
        },
        {
            "text": "2.2 因子构建方法",
            "page": 2,
            "font_size": 12.0,
            "is_heading": True,
            "level": 3,
        },
        {
            "text": "动量因子定义为过去12个月的累计收益率。具体而言，它在每个月末计算股票在过去12个月的收益率。",
            "page": 2,
            "font_size": 11.0,
            "is_heading": False,
            "level": 0,
        },
        {
            "text": "第三章 实证结果",
            "page": 3,
            "font_size": 14.0,
            "is_heading": True,
            "level": 2,
        },
        {
            "text": "3.1 因子表现",
            "page": 3,
            "font_size": 12.0,
            "is_heading": True,
            "level": 3,
        },
        {
            "text": "实证结果显示，动量因子在2020年表现很好，年化超额收益率达到15%。这一结果表明动量效应在中国市场依然存在。",
            "page": 3,
            "font_size": 11.0,
            "is_heading": False,
            "level": 0,
        },
    ]
    
    # Create document
    document = Document(
        metadata=metadata,
        raw_text="\n".join([item["text"] for item in structured_content]),
        structured_content=structured_content,
        images=[],
    )
    
    return document


def main():
    """Run the demonstration"""
    
    print("=" * 70)
    print("paper2chunk 演示 - PDF to RAG-friendly Chunks")
    print("=" * 70)
    print()
    
    # Step 1: Create demo document
    print("📄 Step 1: 创建演示文档...")
    document = create_demo_document()
    print(f"   ✓ 文档标题: {document.metadata.title}")
    print(f"   ✓ 总页数: {document.metadata.total_pages}")
    print(f"   ✓ 文本长度: {len(document.raw_text)} 字符")
    print()
    
    # Step 2: Semantic chunking
    print("📑 Step 2: 语义分片...")
    config = ChunkingConfig(max_chunk_size=300, min_chunk_size=50, overlap_size=30)
    chunker = SemanticChunker(config)
    chunks = chunker.chunk_document(document)
    print(f"   ✓ 生成 {len(chunks)} 个语义分片")
    print()
    
    # Step 3: Inject metadata
    print("🏷️  Step 3: 注入元数据...")
    injector = MetadataInjector()
    chunks = injector.inject_metadata(chunks)
    print(f"   ✓ 为所有分片注入了元数据")
    print()
    
    # Step 4: Display sample chunks
    print("📊 Step 4: 展示分片示例...")
    print()
    
    for i, chunk in enumerate(chunks[:2]):  # Show first 2 chunks
        print(f"--- Chunk {i + 1} ---")
        print(f"章节层级: {' → '.join(chunk.metadata.section_hierarchy)}")
        print(f"页码: {chunk.metadata.page_numbers}")
        print(f"内容长度: {len(chunk.content)} 字符")
        print()
        print("增强内容预览:")
        print(chunk.enhanced_content[:300] if chunk.enhanced_content else chunk.content[:300])
        print("...")
        print()
    
    # Step 5: Format outputs
    print("💾 Step 5: 生成不同格式的输出...")
    print()
    
    # LightRAG format
    lightrag_formatter = LightRAGFormatter()
    lightrag_output = lightrag_formatter.format(chunks)
    print(f"✓ LightRAG 格式: {len(lightrag_output)} 个条目")
    print(f"  示例字段: {list(lightrag_output[0].keys())}")
    
    # LangChain format
    langchain_formatter = LangChainFormatter()
    langchain_output = langchain_formatter.format(chunks)
    print(f"✓ LangChain 格式: {len(langchain_output)} 个条目")
    print(f"  示例字段: {list(langchain_output[0].keys())}")
    
    # Markdown format
    markdown_formatter = MarkdownFormatter()
    markdown_output = markdown_formatter.format(chunks)
    print(f"✓ Markdown 格式: {len(markdown_output)} 字符")
    print()
    
    # Step 6: Show output samples
    print("📋 Step 6: 输出格式示例...")
    print()
    
    print("--- LightRAG 格式 ---")
    import json
    print(json.dumps(lightrag_output[0], indent=2, ensure_ascii=False)[:500])
    print("...\n")
    
    print("--- Markdown 格式 (前500字符) ---")
    print(markdown_output[:500])
    print("...")
    print()
    
    # Summary
    print("=" * 70)
    print("✅ 演示完成!")
    print("=" * 70)
    print()
    print("核心功能展示:")
    print("  ✓ 基于文档结构的语义分片")
    print("  ✓ 自动元数据注入（标题、章节、页码）")
    print("  ✓ 多种输出格式支持（LightRAG、LangChain、Markdown）")
    print("  ✓ 分片独立且语义完整")
    print()
    print("在实际使用中，您还可以:")
    print("  • 使用 LLM 进行语义增强")
    print("  • 自动提取实体和关键词")
    print("  • 转换图表为文字描述")
    print("  • 处理真实的 PDF 文档")
    print()


if __name__ == "__main__":
    main()

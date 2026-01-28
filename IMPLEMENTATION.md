# 4-Layer Architecture Implementation Summary

## 概述 (Overview)

本次重构完全按照 issue 要求，基于**行业 方法**重新构建了文档解析层，引入了全新的 4 层架构。原有的解析层被保留作为向后兼容的传统管道，新的 管道提供了更精确、更智能的文档处理能力。

## 🏗️ 新架构详解

### 1️⃣ 解析层 (The Parser): MinerU 视觉提取
**文件**: `paper2chunk/core/pdf_parser_new.py`

**核心功能**:
- 使用 MinerU (Magic-PDF) API 进行视觉版面分析
- 精准识别：Text, Header, Table, Image, Equation
- 自动过滤页眉页脚等无关信息
- 输出结构化的 Block 列表

**关键特性**:
- PDF 文件大小限制：50MB
- 批量上传 API：使用 MinerU v4 批量上传接口
- 超时设置：可配置（默认 300 秒）
- 异步处理：上传后自动提交解析任务，轮询获取结果
- 详细错误信息：包含文件名、HTTP 状态码等
- API 密钥验证：初始化时检查

**API 流程**:
1. 申请上传链接：调用 `https://mineru.net/api/v4/file-urls/batch`
2. 上传 PDF 文件：使用 PUT 请求上传到返回的 URL
3. 轮询结果：系统自动提交解析任务，轮询 batch 状态获取结果

**数据模型**:
```python
class Block(BaseModel):
    id: str              # 唯一 ID
    type: str           # text, header, table, image, equation
    text: str           # 文本内容
    level: Optional[int] # 标题层级（初始可能不准确）
    page: int           # 页码
    bbox: List[float]   # 边界框
```

### 2️⃣ 逻辑层 (The Logic Repair): LLM 目录树修复
**文件**: `paper2chunk/core/logic_repair.py`

**核心功能**:
- 提取所有 header 形成"骨架"
- 使用 LLM (GPT-4o/Claude) 修正层级（H1-H4）
- 基于编号逻辑（1. vs 1.1）和语义逻辑
- 回填正确的 level 到原始 Block

**关键特性**:
- 智能 fallback：LLM 失败时使用模式推断
- 模式识别：
  - `Chapter X` / `第X章` → H1
  - `1. Title` → H2
  - `1.1 Subtitle` → H3
  - `1.1.1 Detail` → H4
- 详细错误处理：区分 JSON 错误、API 错误等

**算法流程**:
```
提取骨架 → LLM 分析 → 验证结果 → 回填层级
         ↓ (失败)
      模式推断 fallback
```

### 3️⃣ 建模层 (The Tree Builder): AST 构建
**文件**: `paper2chunk/core/tree_builder.py`

**核心功能**:
- 将线性 Block 列表转换为嵌套树结构
- 使用基于栈的构建算法
- 保持文档的层级结构

**数据模型**:
```python
class TreeNode(BaseModel):
    id: str
    type: str              # root, section, content
    title: Optional[str]   # section 标题
    level: Optional[int]   # section 层级
    content: str           # content 内容
    children: List[TreeNode]
```

**算法**:
```python
stack = [root]
for block in blocks:
    if block.type == 'header':
        # 弹出所有 level >= current.level 的节点
        while stack[-1].level >= block.level:
            stack.pop()
        # 创建新节点，挂载到栈顶，入栈
        new_node = create_section_node(block)
        stack[-1].children.append(new_node)
        stack.append(new_node)
    else:
        # 内容节点直接挂载到栈顶
        content_node = create_content_node(block)
        stack[-1].children.append(content_node)
```

### 4️⃣ 切片层 (The Slicer): 双阈值递归 DFS
**文件**: `paper2chunk/core/semantic_chunker_new.py`

**核心功能**:
- 基于双阈值递归深度优先搜索
- 原则：**结构边界 > 内容长度**
- 使用 tiktoken 精确计算 token 数

**参数**:
- **Soft Limit** (默认 800 tokens): 最佳长度
- **Hard Limit** (默认 2000 tokens): 最大长度

**算法逻辑**:

```python
def recursive_dfs(node, section_hierarchy):
    tokens = node.get_total_tokens()
    
    # Base Case: 小于软限制，保持完整
    if tokens < SOFT_LIMIT:
        create_chunk(collect_content(node))
        return
    
    # Recursive Case: 大于软限制，需要拆分
    if node.has_children():
        # 合并小兄弟，递归处理大兄弟
        for child in node.children:
            if child.tokens < SOFT_LIMIT:
                accumulate(child)
            else:
                flush_accumulated()
                recursive_dfs(child)
    else:
        # Edge Case: 叶子节点超大
        if tokens > HARD_LIMIT:
            llm_semantic_split(node)  # LLM 语义拆解
        else:
            create_chunk(node)
```

**关键特性**:
- 精确 token 计数（使用 tiktoken cl100k_base）
- LLM 语义拆分：
  - 发送上下文给 LLM
  - 请求语义边界的分割点
  - 验证分割点（范围、顺序）
  - 创建子 chunks
- Fallback 机制：LLM 失败时简单字符切分

## 📊 完整流程示例

```
input.pdf
    ↓
【Layer 1: MinerU Parser】
    → API 调用
    → 版面分析
    → 提取 200 个 blocks
    ↓
【Layer 2: Logic Repairer】
    → 提取 30 个 headers
    → LLM 修正层级
    → 回填 level 属性
    ↓
【Layer 3: Tree Builder】
    → 构建 AST (65 nodes)
    → 根节点 → 章节节点 → 内容节点
    ↓
【Layer 4: Dual-Threshold Chunker】
    → DFS 遍历树
    → 智能合并/拆分
    → 生成 45 chunks
    ↓
【Optional: Metadata Injection】
    → 注入标题、章节、页码
    ↓
【Optional: LLM Enhancement】
    → 语义增强
    → 提取实体和关键词
    ↓
output.json (RAG-ready chunks)
```

## 🚀 使用方式

### 命令行

```bash
# 使用新 管道
paper2chunk input.pdf -o output.json --sota

# 自定义参数
paper2chunk input.pdf -o output.json --sota \
  --soft-limit 1000 \
  --hard-limit 2500 \
  --no-enhancement

# 使用传统管道（向后兼容）
paper2chunk input.pdf -o output.json
```

### Python API

```python
from paper2chunk import Paper2ChunkSOTAPipeline
from paper2chunk.config import Config

# 配置
config = Config.from_env()
config.chunking.soft_limit = 800
config.chunking.hard_limit = 2000

# 初始化管道
pipeline = Paper2ChunkSOTAPipeline(config)

# 处理文档
document = pipeline.process("example.pdf")

# 保存结果
pipeline.save_output(document, "output.json", "lightrag")

# 访问 chunks
for chunk in document.chunks:
    print(chunk.content)
    print(chunk.metadata.section_hierarchy)
    print(chunk.entities)
```

## ⚙️ 配置要求

### 必需配置

```bash
# MinerU API (批量上传接口)
# 获取密钥: https://mineru.net/
MINERU_API_KEY=your_key_here

# LLM (选择一个)
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o
# 或
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-opus-20240229

LLM_PROVIDER=openai  # 或 anthropic
```

### 可选配置

```bash
# 分片参数（token 数）
CHUNK_SOFT_LIMIT=800
CHUNK_HARD_LIMIT=2000

# MinerU API 高级配置
MINERU_TIMEOUT=300              # 上传超时（秒）
MINERU_POLL_INTERVAL=5          # 轮询间隔（秒）
MINERU_MAX_POLL_ATTEMPTS=60     # 最大轮询次数

# 功能开关
ENABLE_SEMANTIC_ENHANCEMENT=true
ENABLE_CHART_TO_TEXT=true
ENABLE_METADATA_INJECTION=true

# MinerU 超时（秒）
MINERU_TIMEOUT=300
```

## 🔒 安全性

已通过 CodeQL 安全扫描，无安全漏洞。

**关键安全措施**:
- PDF 文件大小限制（50MB）
- API 密钥验证
- 安全的环境变量解析
- 超时保护
- 错误边界处理

## ✅ 代码质量

**已实施**:
- ✅ 完整的类型提示 (Type Hints)
- ✅ 详细的文档字符串 (Docstrings)
- ✅ 全面的错误处理和验证
- ✅ 安全的配置解析
- ✅ 精确的 token 计数（tiktoken）
- ✅ 模块化设计
- ✅ 向后兼容性

**代码审查反馈已全部解决**:
- PDF 文件大小验证 ✅
- 详细错误信息 ✅
- tiktoken 精确计数 ✅
- LLM 响应验证 ✅
- API 密钥提前验证 ✅
- 安全的整数解析 ✅
- 改进的 fallback 机制 ✅

## 📈 性能特点

| 特性 | 管道 | 传统管道 |
|-----|----------|---------|
| 版面识别 | ⭐⭐⭐⭐⭐ 视觉 AI | ⭐⭐⭐ 启发式 |
| 层级准确性 | ⭐⭐⭐⭐⭐ LLM 修复 | ⭐⭐ 字体大小 |
| 结构保持 | ⭐⭐⭐⭐⭐ AST | ⭐⭐⭐ 部分 |
| 智能切片 | ⭐⭐⭐⭐⭐ 双阈值 DFS | ⭐⭐⭐ 简单规则 |
| Token 精度 | ⭐⭐⭐⭐⭐ tiktoken | ⭐⭐ 字符估算 |
| 语义完整性 | ⭐⭐⭐⭐⭐ 极高 | ⭐⭐⭐ 中等 |

## 🎯 关键创新点

1. **MinerU 集成**: 行业领先的 PDF 视觉解析
2. **LLM 层级修复**: 自动修正目录结构
3. **AST 建模**: 从线性到树状的升维
4. **双阈值 DFS**: 结构优先的智能切片
5. **tiktoken 精确计数**: 准确的 token 管理
6. **LLM 手术刀**: 超大块的语义拆解
7. **智能 Fallback**: 多层次的容错机制

## 📦 文件清单

### 新增核心模块
- `paper2chunk/core/pdf_parser_new.py` - MinerU 解析器
- `paper2chunk/core/logic_repair.py` - LLM 层级修复
- `paper2chunk/core/tree_builder.py` - AST 构建器
- `paper2chunk/core/semantic_chunker_new.py` - 双阈值分片器
- `paper2chunk/pipeline_sota.py` - 管道

### 更新模块
- `paper2chunk/models.py` - 新增 Block, TreeNode 模型
- `paper2chunk/config.py` - 新增 MinerUConfig，更新参数
- `paper2chunk/cli.py` - 支持 --sota 标志
- `paper2chunk/__init__.py` - 导出新模块

### 文档
- `README.md` - 完整的使用文档
- `README_OLD.md` - 原始 README（备份）
- `SOTA_IMPLEMENTATION.md` - 本文档

### 示例
- `examples/pipeline_example.py` - 管道示例

### 依赖
- `requirements.txt` - 新增 requests, tiktoken

## 🔄 向后兼容性

**保留的传统模块**:
- `paper2chunk/core/pdf_parser.py` - PyMuPDF 解析器
- `paper2chunk/core/semantic_chunker.py` - 传统分片器
- `paper2chunk/pipeline.py` - 传统管道

**迁移路径**:
- 默认使用传统管道（无 API 密钥要求）
- 添加 `--sota` 标志使用新管道
- 或使用 `Paper2ChunkSOTAPipeline` API

## 🎓 适用场景

**推荐使用 管道**:
- 📄 复杂的学术论文
- 📊 金融研究报告
- 📚 技术文档
- ⚖️ 法律文件
- 🏢 企业知识库

**可以使用传统管道**:
- 📝 简单文档
- 🚀 快速原型
- 💰 API 成本敏感场景
- 🔒 离线环境

## 🙏 致谢

- **MinerU (Magic-PDF)**: 提供 PDF 视觉解析能力
- **OpenAI GPT-4o**: 提供层级修复和语义拆解
- **tiktoken**: 提供精确的 token 计数
- **Issue 提出者**: 提供清晰的需求和架构指导

---

**实现者**: GitHub Copilot  
**日期**: 2026-01-28  
**状态**: ✅ 完成并通过代码审查

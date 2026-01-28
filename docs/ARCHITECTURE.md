# paper2chunk 架构说明

本文档描述 `paper2chunk` 的整体架构、核心数据模型，以及两条处理管道（默认 4 层架构 + 传统管道）。

## 目标

`paper2chunk` 的目标是把 PDF 转换为 **RAG 友好** 的语义分片（chunks），并尽量保证：
- **结构边界优先**：章节/小节优于固定长度切分
- **分片可独立理解**：注入必要的上下文/元数据
- **可选语义增强**：LLM 消解代词、显式化隐含信息、抽取实体/关键词

## 两条管道

### 1) 默认管道（4 层架构：MinerU + LLM）

适用于版面复杂、标题层级不稳定的论文/研报类 PDF。

```
PDF
  ↓
解析层（MinerUParser）：视觉版面分析 → Block 列表
  ↓
逻辑层（LogicRepairer）：LLM 修复标题层级 → 修正后的 Block
  ↓
建模层（TreeBuilder）：Block 折叠为 AST（TreeNode）
  ↓
切片层（DualThresholdChunker）：双阈值递归 DFS → Chunk 列表
  ↓
（可选）MetadataInjector / LLMRewriter / ChartAnalyzer
  ↓
输出（LightRAG / LangChain / Markdown / JSON）
```

关键文件：
- `paper2chunk/core/pdf_parser_new.py`：MinerU 解析（视觉提取）
- `paper2chunk/core/logic_repair.py`：目录层级修复（LLM + fallback）
- `paper2chunk/core/tree_builder.py`：AST 构建（栈算法）
- `paper2chunk/core/semantic_chunker_new.py`：双阈值 DFS 切片
- `paper2chunk/pipeline.py`：默认管道编排

#### 解析层：MinerU 视觉提取

文件：`paper2chunk/core/pdf_parser_new.py`

做什么：
- 上传 PDF → MinerU 进行视觉版面分析（Layout Analysis）
- 产出结构化 Block：`text/header/table/image/equation` 等
- 过滤页眉页脚等噪音（依赖 MinerU 输出）

依赖配置：
- 需要 `MINERU_API_KEY`
- 超时与轮询参数可配置（见 `paper2chunk/config.py` 的 `MinerUConfig`）

#### 逻辑层：LLM 目录树修复（标题层级）

文件：`paper2chunk/core/logic_repair.py`

痛点：
- 视觉解析通常能识别“这是标题”，但层级（H1/H2/H3…）不稳定

做法：
- 提取标题骨架（header 列表）
- 交给 LLM 标注层级，并将修正后的 `level` 回填到 Block
- 若 LLM 失败，采用规则 fallback（编号模式、章节模式等）

#### 建模层：AST 构建（栈算法）

文件：`paper2chunk/core/tree_builder.py`

目标：
- 把线性的 Block 列表折叠为树（`TreeNode`），恢复文档层级结构

思路：
- 使用栈维护当前章节路径
- 遇到 header：根据 level 弹栈到合适层级，再挂载新节点入栈
- 遇到正文/表格等：挂到栈顶节点

#### 切片层：双阈值递归 DFS（结构优先）

文件：`paper2chunk/core/semantic_chunker_new.py`

目标：
- “结构边界 > 内容长度”，在保证结构完整的前提下，尽量控制 chunk 大小

参数：
- `soft_limit`：最佳长度（token）
- `hard_limit`：最大长度（token）

策略（简述）：
- 若节点（含子树）token 数 < `soft_limit`：整体作为一个 chunk
- 否则：递归处理子节点，并尝试合并小块
- 叶子节点 > `hard_limit`：可选调用 LLM 做语义拆分（若配置了 LLM）

### 2) 传统管道（PyMuPDF，向后兼容）

适用于不希望依赖 MinerU/LLM（或仅需本地启发式解析）的场景。

关键文件：
- `paper2chunk/core/pdf_parser.py`
- `paper2chunk/core/semantic_chunker.py`
- `paper2chunk/pipeline_legacy.py`

## 数据模型（高层）

模型定义在 `paper2chunk/models.py`，主要包括：
- `Block`：解析层输出的“版面块”
- `TreeNode`：建模层输出的“树节点”
- `Chunk` / `ChunkMetadata`：切片结果及元数据
- `Document`：贯穿全流程的文档对象（含元信息、blocks/tree/chunks 等）

## 输出格式

输出格式化器位于 `paper2chunk/output_formatters/`：
- `lightrag`：面向 Graph RAG（包含实体/关键词等字段）
- `langchain`：LangChain `Document` 风格结构
- `markdown`：便于人类阅读/二次处理
- `json`：通用 JSON


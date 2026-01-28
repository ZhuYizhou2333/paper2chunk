"""基于 LLM 的文本改写器（语义增强）

本模块统一使用 OpenAI 官方 Python SDK，并支持通过 `base_url` 指向任意 OpenAI 兼容的 API 端点。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from paper2chunk.config import LLMConfig
from paper2chunk.models import Chunk

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


class LLMRewriter:
    """使用 LLM 对 chunk 做语义增强（代词消解、信息显式化、实体加粗等）。"""

    def __init__(self, config: LLMConfig):
        self.config = config

        if OpenAI is None:
            raise ImportError("缺少依赖：openai。请使用 `uv sync` 安装依赖后重试。")
        if not self.config.api_key:
            raise ValueError("缺少 LLM API Key：请设置环境变量 OPENAI_API_KEY。")

        client_kwargs = {"api_key": self.config.api_key}
        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url
        self.client = OpenAI(**client_kwargs)

    def enhance_chunk(self, chunk: Chunk, document_title: str, section_hierarchy: List[str]) -> str:
        """对单个 chunk 做语义增强。"""
        context = self._build_context(document_title, section_hierarchy, chunk.metadata.publish_date)
        prompt = self._build_enhancement_prompt(chunk.content, context)
        return self._chat_text(prompt, system="你是面向 RAG 系统的语义增强专家。")

    def extract_entities_and_keywords(self, text: str) -> Tuple[List[str], List[str]]:
        """抽取实体与关键词（返回 entities, keywords）。"""
        prompt = f"""请从下面文本中抽取关键实体与关键词，并返回 JSON。

文本：
{text}

要求：
- 返回一个 JSON 对象，包含两个数组字段：
  - "entities": 命名实体（人名/机构/地点/概念等）
  - "keywords": 重要关键词或短语
- 只返回 JSON，不要额外解释，不要 Markdown 代码块。

示例：
{{
  "entities": ["实体1", "实体2"],
  "keywords": ["关键词1", "关键词2"]
}}
"""
        result = self._chat_text(prompt, system="你是信息抽取专家。")

        try:
            import json

            data = json.loads(result)
            return data.get("entities", []) or [], data.get("keywords", []) or []
        except Exception as e:
            print(f"Error extracting entities/keywords: {type(e).__name__}: {e}")
            return [], []

    def _chat_text(self, prompt: str, system: str) -> str:
        """通过 Chat Completions 获取文本输出。"""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            print(f"Error calling OpenAI-compatible API: {type(e).__name__}: {e}")
            return ""

    @staticmethod
    def _build_context(document_title: str, section_hierarchy: List[str], publish_date: Optional[str]) -> str:
        """从元数据构建上下文提示。"""
        context_parts = [f"文档：{document_title}"]
        if section_hierarchy:
            context_parts.append(f"章节：{' > '.join(section_hierarchy)}")
        if publish_date:
            context_parts.append(f"日期：{publish_date}")
        return " | ".join(context_parts)

    @staticmethod
    def _build_enhancement_prompt(content: str, context: str) -> str:
        """构建语义增强 prompt。"""
        return f"""你需要对给定文本做“语义增强”，以便更适合用于 RAG 检索与问答。

上下文：{context}

原文：
{content}

要求：
1. 消解代词与指代（例如“它/这/该方法”→ 明确为具体实体或概念）
2. 将隐含信息显式化（例如“在 2020 年”→ “在【2020 年】”）
3. 必要时结合章节层级补充关键上下文（不要编造原文没有的信息）
4. 保留原意与所有事实信息，不要删减关键内容
5. 对关键实体与概念使用 **加粗**
6. 结果保持简洁、可读

请直接输出增强后的文本："""


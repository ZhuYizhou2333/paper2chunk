"""逻辑层：目录树（标题层级）修复

核心思路：
- 从 MinerU 的输出中抽取“骨架”（所有标题）。
- 交给 LLM 仅做层级标注（level=1..4），再回填到对应 Block。
- 若 LLM 不可用/返回异常，则使用规则推断作为兜底。

注意：本项目统一使用 OpenAI 官方 Python SDK，并支持通过 `base_url` 连接自定义 OpenAI 兼容端点。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from paper2chunk.config import LLMConfig
from paper2chunk.models import Block

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


class LogicRepairer:
    """使用 LLM 修复标题层级（H1~H4）。"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._init_llm_client()

    def _init_llm_client(self) -> None:
        """初始化 OpenAI 兼容客户端。"""
        if OpenAI is None:
            raise ImportError("缺少依赖：openai。请使用 `uv sync` 安装依赖后重试。")
        if not self.config.api_key:
            raise ValueError("缺少 LLM API Key：请设置环境变量 OPENAI_API_KEY。")

        client_kwargs = {"api_key": self.config.api_key}
        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url
        self.client = OpenAI(**client_kwargs)

    def repair_hierarchy(self, blocks: List[Block]) -> List[Block]:
        """修复 blocks 中标题（type=header）的 level。"""
        print("Repairing header hierarchy with LLM...")

        skeleton = self._extract_skeleton(blocks)
        if not skeleton:
            print("  ✓ No headers found, skipping hierarchy repair")
            return blocks

        corrected = self._llm_repair(skeleton)
        blocks = self._write_back_levels(blocks, corrected)

        print(f"  ✓ Repaired hierarchy for {len(skeleton)} headers")
        return blocks

    @staticmethod
    def _extract_skeleton(blocks: List[Block]) -> List[Dict[str, Any]]:
        """抽取标题骨架。"""
        skeleton: List[Dict[str, Any]] = []
        for block in blocks:
            if block.type == "header":
                skeleton.append(
                    {
                        "id": block.id,
                        "text": block.text,
                        "original_level": block.level,
                    }
                )
        return skeleton

    def _llm_repair(self, skeleton: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """调用 LLM 为每个标题标注层级（level=1..4）。"""
        skeleton_text = "\n".join([f"{i}. {item['text']}" for i, item in enumerate(skeleton)])

        prompt = f"""你在分析一份文档的目录结构。下面是从 PDF 中抽取出的标题列表，但其层级（H1/H2/H3/H4）缺失或不准确。

请根据编号规律（例如 1 vs 1.1 vs 1.1.1）和语义规律（例如 Introduction 通常是顶层）为每一行分配正确层级。

标题列表（index 从 0 开始）：
{skeleton_text}

规则：
- level=1：顶层章节/主章
- level=2：章节内小节
- level=3：子小节
- level=4：更深层子小节

输出要求：
- 只返回 JSON 数组，不要解释，不要 Markdown 代码块。
- 数组元素格式为：{{"index": 0, "level": 1}}

JSON："""

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "你是文档结构分析专家，只返回合法 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=min(2000, self.config.max_tokens),
            )
            result_text = (response.choices[0].message.content or "").strip()
            result_text = self._strip_code_fences(result_text)
            corrected_levels = json.loads(result_text)

            for item in corrected_levels:
                idx = int(item.get("index", -1))
                level = int(item.get("level", 0))
                if 0 <= idx < len(skeleton) and 1 <= level <= 4:
                    skeleton[idx]["corrected_level"] = level

            # 若部分缺失，继续用兜底补齐
            for item in skeleton:
                if "corrected_level" not in item:
                    item["corrected_level"] = item.get("original_level") or self._infer_level(item["text"])

            return skeleton

        except json.JSONDecodeError as e:
            print(f"  Warning: Failed to parse LLM response as JSON: {e}")
            print("  Using original levels as fallback")
            for item in skeleton:
                item["corrected_level"] = item.get("original_level") or self._infer_level(item["text"])
            return skeleton
        except Exception as e:
            print(f"  Warning: LLM hierarchy repair failed: {type(e).__name__}: {e}")
            print("  Using original levels as fallback")
            for item in skeleton:
                item["corrected_level"] = item.get("original_level") or self._infer_level(item["text"])
            return skeleton

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """去掉可能出现的 Markdown 代码块包裹。"""
        if "```" not in text:
            return text
        # 优先 ```json
        if "```json" in text:
            return text.split("```json", 1)[1].split("```", 1)[0].strip()
        return text.split("```", 1)[1].split("```", 1)[0].strip()

    @staticmethod
    def _infer_level(text: str) -> int:
        """规则兜底：从文本模式推断标题层级（1-4）。"""
        if re.match(r"^(Chapter|第[一二三四五六七八九十\\d]+章)", text, re.IGNORECASE):
            return 1
        if re.match(r"^\\d+\\.\\s", text):  # "1. Introduction"
            return 2
        if re.match(r"^\\d+\\.\\d+\\s", text):  # "1.1 Background"
            return 3
        if re.match(r"^\\d+\\.\\d+\\.\\d+\\s", text):  # "1.1.1 Details"
            return 4
        return 2

    @staticmethod
    def _write_back_levels(blocks: List[Block], corrected_skeleton: List[Dict[str, Any]]) -> List[Block]:
        """把修复后的 level 回填到 blocks。"""
        level_map = {
            item["id"]: item.get("corrected_level", item.get("original_level", 1)) for item in corrected_skeleton
        }

        updated: List[Block] = []
        for block in blocks:
            if block.id in level_map:
                block_dict = block.model_dump()
                block_dict["level"] = level_map[block.id]
                block = Block(**block_dict)
            updated.append(block)

        return updated


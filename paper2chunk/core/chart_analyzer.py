"""图片/图表视觉解析与文本注入（图片必须可检索）

目标：
- 对 Document.images 中的图片调用“可配置的视觉模型”生成文本描述
- 将图片的提取信息（caption/footnote/尺寸等）与 LLM 生成描述一起注入到文段中

设计约定：
- 默认管道（MinerU）里，图片会以 Block(type="image") 形式出现在 blocks 中，但其 text 可能为空。
  本模块会把图片信息写回到对应 Block.text，确保后续 TreeBuilder/Chunker 能检索到图片内容。
- 传统管道（PyMuPDF）里没有 blocks，本模块会把图片描述追加进 structured_content/raw_text，
  至少保证图片信息能进入 chunking（位置不一定精准，但可检索）。
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List, Optional

from PIL import Image
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from paper2chunk.config import LLMConfig
from paper2chunk.models import Block, Document

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


@dataclass(frozen=True)
class _VisionImage:
    """发送到视觉模型前的图片封装。"""

    data_url: str
    width: int
    height: int
    sha256: str


@dataclass(frozen=True)
class _ExtractedImageFields:
    """从解析结果中提取的图片字段（用于注入与提示词）。"""

    page: int
    img_path: str
    width: int
    height: int
    caption: str
    footnote: str


class ChartAnalyzer:
    """图片/图表转文本描述器（使用 OpenAI 兼容视觉模型）。"""

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

        self._cache: Dict[str, str] = {}

    def analyze_images_in_document(self, images: list, document_title: str) -> Dict[str, str]:
        """对图片列表生成描述（仅生成，不注入）。"""

        descriptions: Dict[str, str] = {}
        if not images:
            return descriptions

        progress_columns = [
            SpinnerColumn(),
            TextColumn("[bold]{task.description}[/bold]"),
            BarColumn(bar_width=None),
            TextColumn("{task.completed}/{task.total} 张"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ]

        with Progress(*progress_columns, transient=True) as progress:
            task = progress.add_task("视觉模型生成图片描述", total=len(images))

            for img in images:
                key = self._image_key(img)
                try:
                    desc = self.describe_image(img, document_title=document_title)
                    if desc:
                        descriptions[key] = desc
                finally:
                    progress.advance(task, 1)

        return descriptions

    def inject_image_descriptions_into_blocks(
        self,
        blocks: List[Block],
        images: List[Dict[str, Any]],
        document_title: str,
        enable_llm: bool = True,
    ) -> None:
        """把图片信息（提取+LLM）写回到 blocks 中的 image 块。

        - 修改 blocks：对每个 Block(type="image") 写入 Block.text
        - 修改 images：写入 llm_description / injected_text 便于输出侧消费
        """

        if not blocks:
            return

        image_by_path: Dict[str, Dict[str, Any]] = {}
        for img in images:
            img_path = img.get("img_path")
            if isinstance(img_path, str) and img_path:
                image_by_path[img_path] = img

        image_blocks = [b for b in blocks if b.type == "image"]
        if not image_blocks:
            return

        progress_columns = [
            SpinnerColumn(),
            TextColumn("[bold]{task.description}[/bold]"),
            BarColumn(bar_width=None),
            TextColumn("{task.completed}/{task.total} 张"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ]

        with Progress(*progress_columns, transient=True) as progress:
            task = progress.add_task("注入图片信息到文段", total=len(image_blocks))

            for block in image_blocks:
                try:
                    img_path = block.metadata.get("img_path")
                    img = image_by_path.get(img_path) if isinstance(img_path, str) else None

                    extracted = self._extract_image_fields(block, img)
                    llm_description = ""
                    if enable_llm:
                        llm_description = self.describe_image(img or {}, document_title=document_title, extracted=extracted)

                    injected = self._format_injected_text(
                        extracted=extracted,
                        llm_description=llm_description,
                    )

                    block.text = injected

                    if img is not None:
                        img["llm_description"] = llm_description
                        img["injected_text"] = injected
                        img["caption"] = extracted.caption
                        img["footnote"] = extracted.footnote

                finally:
                    progress.advance(task, 1)

    def inject_images_into_legacy_document(self, document: Document, enable_llm: bool = True) -> None:
        """传统管道注入：把图片描述追加进 structured_content/raw_text。"""

        if not document.images:
            return

        additions: List[Dict[str, Any]] = []
        for img in document.images:
            extracted = self._extract_image_fields(block=None, img=img)
            llm_description = self.describe_image(img, document_title=document.metadata.title, extracted=extracted) if enable_llm else ""
            injected = self._format_injected_text(extracted=extracted, llm_description=llm_description)

            img["llm_description"] = llm_description
            img["injected_text"] = injected

            additions.append(
                {
                    "text": injected,
                    "page": img.get("page", 1),
                    "font_size": 0,
                    "is_heading": False,
                    "level": 0,
                }
            )

        # 简单策略：按页排序后追加到 structured_content 末尾（至少保证可检索）
        additions.sort(key=lambda x: int(x.get("page") or 1))
        document.structured_content.extend(additions)

        # 同步 raw_text（避免走 raw_text fallback 时丢失图片信息）
        document.raw_text = (document.raw_text or "").rstrip() + "\n\n" + "\n\n".join(a["text"] for a in additions)

    def describe_image(
        self,
        image_info: Dict[str, Any],
        document_title: str,
        extracted: Optional[_ExtractedImageFields] = None,
    ) -> str:
        """调用视觉模型生成图片描述（带缓存）。"""

        image_bytes = image_info.get("image_data")
        if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
            return ""

        vision_image = self._prepare_vision_image(bytes(image_bytes))
        cache_key = vision_image.sha256 + "|" + (self.config.vision_model or self.config.model)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        prompt = self._build_vision_prompt(
            document_title=document_title,
            page=int(image_info.get("page") or 0),
            extracted=extracted,
        )

        description = self._chat_vision(prompt=prompt, image=vision_image)
        description = (description or "").strip()
        self._cache[cache_key] = description
        return description

    def _chat_vision(self, prompt: str, image: _VisionImage) -> str:
        """通过 Chat Completions 发送图文消息并获取文本输出。"""

        model = self.config.vision_model or self.config.model
        detail = self.config.vision_detail or "low"
        if detail not in {"low", "high", "auto"}:
            detail = "low"

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是严谨的视觉理解与信息提取助手。"},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image.data_url, "detail": detail}},
                        ],
                    },
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.vision_max_tokens,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            print(f"Error calling vision model: {type(e).__name__}: {e}")
            return ""

    def _image_key(self, img: Dict[str, Any]) -> str:
        img_path = img.get("img_path")
        if isinstance(img_path, str) and img_path:
            return img_path
        page = img.get("page", 0)
        index = img.get("index", 0)
        return f"page_{page}_img_{index}"

    def _prepare_vision_image(self, image_bytes: bytes) -> _VisionImage:
        """对图片做压缩与缩放，生成 data URL。"""

        sha256 = hashlib.sha256(image_bytes).hexdigest()

        try:
            with Image.open(BytesIO(image_bytes)) as im:
                im = im.convert("RGB")
                width, height = im.size

                max_side = 1024
                if max(width, height) > max_side:
                    scale = max_side / float(max(width, height))
                    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
                    im = im.resize(new_size)
                    width, height = im.size

                buf = BytesIO()
                im.save(buf, format="JPEG", quality=85, optimize=True)
                jpeg_bytes = buf.getvalue()
        except Exception:
            # 兜底：直接用原始 bytes（可能是 png/jpg）
            width = 0
            height = 0
            jpeg_bytes = image_bytes

        data_url = "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode("utf-8")
        return _VisionImage(data_url=data_url, width=width, height=height, sha256=sha256)

    def _build_vision_prompt(
        self,
        document_title: str,
        page: int,
        extracted: Optional[_ExtractedImageFields],
    ) -> str:
        """构建视觉描述提示词（中文输出，方便注入到文段中）。"""

        caption = extracted.caption if extracted else ""
        footnote = extracted.footnote if extracted else ""

        return f"""请对给定图片生成一个“可用于 RAG 检索”的文本描述，要求严格依据图片内容，不要臆造。

上下文：
- 文档：{document_title}
- 页码：{page if page else "未知"}
- 提取到的图片标题（可能为空）：{caption or "（无）"}
- 提取到的图片脚注（可能为空）：{footnote or "（无）"}

输出要求：
1) 输出中文
2) 先用 1 句话概括图片类型与主题
3) 再用 3~8 条要点列出关键可检索信息（变量、数值趋势、坐标轴、表头、方法流程、结论等）
4) 如果是表格或图表，请明确说明列/行含义或坐标轴含义
5) 不要输出 Markdown 代码块
"""

    def _extract_image_fields(
        self, block: Optional[Block], img: Optional[Dict[str, Any]]
    ) -> _ExtractedImageFields:
        """从 MinerU block + images 里提取可注入字段（caption/footnote/尺寸等）。"""

        page = 0
        img_path = ""
        width = 0
        height = 0
        caption = ""
        footnote = ""

        if block is not None:
            page = int(block.page or 0)
            meta_path = block.metadata.get("img_path")
            if isinstance(meta_path, str):
                img_path = meta_path

            cap = block.metadata.get("image_caption")
            if isinstance(cap, list):
                caption = " ".join(str(x).strip() for x in cap if str(x).strip())
            elif isinstance(cap, str):
                caption = cap.strip()

            foot = block.metadata.get("image_footnote")
            if isinstance(foot, list):
                footnote = " ".join(str(x).strip() for x in foot if str(x).strip())
            elif isinstance(foot, str):
                footnote = foot.strip()

        if img is not None:
            page = page or int(img.get("page") or 0)
            img_path = img_path or (img.get("img_path") if isinstance(img.get("img_path"), str) else "")
            width = int(img.get("width") or 0)
            height = int(img.get("height") or 0)

        return _ExtractedImageFields(
            page=page,
            img_path=img_path,
            width=width,
            height=height,
            caption=caption,
            footnote=footnote,
        )

    def _format_injected_text(self, extracted: _ExtractedImageFields, llm_description: str) -> str:
        """生成注入到文段的最终文本。"""

        parts: List[str] = []
        parts.append("【图片】")
        if extracted.page:
            parts.append(f"页码：{extracted.page}")
        if extracted.img_path:
            parts.append(f"路径：{extracted.img_path}")
        if extracted.width and extracted.height:
            parts.append(f"尺寸：{extracted.width}×{extracted.height}")
        if extracted.caption:
            parts.append(f"标题：{extracted.caption}")
        if extracted.footnote:
            parts.append(f"脚注：{extracted.footnote}")

        if llm_description:
            parts.append("视觉描述：")
            parts.append(llm_description.strip())
        else:
            parts.append("视觉描述：（未生成）")

        return "\n".join(parts).strip()

"""MinerU（Magic-PDF）解析器（默认管道第 1 层）

本模块对接 MinerU v4 API，完成以下工作：
1) 通过批量接口申请上传 URL（本地文件必须走该流程）
2) 上传 PDF
3) 轮询批量任务结果（/api/v4/extract-results/batch/{batch_id}）
4) 下载解析结果 zip，并从其中的 *_content_list.json 构建 Block 列表

说明：
- 旧实现曾轮询 /api/v4/batches/{batch_id}，该路径会返回 404，导致一直重试直至超时。
- MinerU 的最终结果通常以 zip 形式提供，建议消费 *_content_list.json（扁平、阅读顺序友好）。
"""

from __future__ import annotations

import json
import time
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from PIL import Image
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from paper2chunk.config import MinerUConfig
from paper2chunk.models import Block, Document, DocumentMetadata


@dataclass(frozen=True)
class _MinerUBatchItem:
    """批量结果中单个文件的状态信息（做轻量归一化）。"""

    state: str
    full_zip_url: Optional[str]
    err_msg: str
    data_id: Optional[str] = None
    task_id: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class MinerUParser:
    """使用 MinerU v4 API 解析 PDF，并产出 Block 列表。"""

    def __init__(self, config: MinerUConfig):
        self.config = config
        if not self.config.api_key:
            raise ValueError("MinerU API key is required. Set MINERU_API_KEY in environment.")

    def parse(self, pdf_path: str) -> Document:
        """解析 PDF（上传→轮询→下载 zip→解析 content_list）。"""

        print(f"Parsing PDF with MinerU: {pdf_path}")

        pdf_file = Path(pdf_path)
        self._validate_pdf_size(pdf_file)

        data_id = pdf_file.stem
        batch_id, upload_url = self._request_batch_upload_url(pdf_file.name, data_id=data_id)
        print(f"  → Got upload URL (batch_id: {batch_id})")

        self._upload_pdf(upload_url, pdf_file)
        print("  → PDF uploaded successfully")

        print("  → Polling for parsing results...")
        batch_item = self._poll_extract_results_batch(batch_id=batch_id, data_id=data_id)
        if batch_item.state != "done":
            raise RuntimeError(f"解析未完成但轮询结束：state={batch_item.state}")
        if not batch_item.full_zip_url:
            raise RuntimeError("解析完成但未返回 full_zip_url，无法下载结果。")

        content_list, images_by_path = self._download_and_read_content_list(
            full_zip_url=batch_item.full_zip_url
        )
        blocks, images, total_pages = self._convert_content_list(
            content_list=content_list, images_by_path=images_by_path
        )

        metadata = DocumentMetadata(
            title=pdf_file.stem,
            source=str(pdf_file),
            total_pages=total_pages,
        )
        raw_text = self._extract_raw_text(blocks)

        document = Document(metadata=metadata, raw_text=raw_text, blocks=blocks, images=images)
        print(f"  ✓ Parsed {len(blocks)} blocks from {metadata.total_pages} pages")
        return document

    def _validate_pdf_size(self, pdf_file: Path) -> None:
        """检查文件大小（MinerU 侧通常有大小限制，这里做前置提示）。"""

        file_size = pdf_file.stat().st_size
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            raise ValueError(
                f"PDF 文件过大：{file_size / (1024 * 1024):.1f}MB，"
                f"最大支持：{max_size / (1024 * 1024):.0f}MB"
            )

    def _request_batch_upload_url(self, filename: str, data_id: str) -> Tuple[str, str]:
        """向 MinerU 申请批量上传 URL。

        官方示例接口：
        POST /api/v4/file-urls/batch
        """

        url = f"{self.config.api_base_url}/api/v4/file-urls/batch"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        payload = {
            "files": [{"name": filename, "data_id": data_id}],
            "model_version": "vlm",
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get("code") != 0:
            raise RuntimeError(f"申请上传 URL 失败：{result.get('msg', 'Unknown error')}")

        batch_id = result["data"]["batch_id"]
        file_urls = result["data"]["file_urls"]
        if not file_urls:
            raise RuntimeError("MinerU 未返回 file_urls。")
        return batch_id, file_urls[0]

    def _upload_pdf(self, upload_url: str, pdf_file: Path) -> None:
        """上传 PDF 到预签名 URL。"""

        with pdf_file.open("rb") as f:
            res = requests.put(upload_url, data=f, timeout=self.config.timeout)
            res.raise_for_status()

    def _poll_extract_results_batch(self, batch_id: str, data_id: Optional[str]) -> _MinerUBatchItem:
        """轮询批量任务结果。

        官方接口（用户提供）：
        GET /api/v4/extract-results/batch/{batch_id}
        """

        url = f"{self.config.api_base_url}/api/v4/extract-results/batch/{batch_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        progress_columns = [
            SpinnerColumn(),
            TextColumn("[bold]{task.description}[/bold]"),
            BarColumn(bar_width=None),
            TextColumn("{task.completed}/{task.total} 页"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ]

        with Progress(*progress_columns, transient=True) as progress:
            task = progress.add_task("MinerU 解析中（初始化）", total=1, completed=0)

            for attempt in range(self.config.max_poll_attempts):
                try:
                    response = requests.get(url, headers=headers, timeout=30)
                    # 这类 4xx 往往是“确定不会成功”的错误，尽早失败更友好
                    if response.status_code in {401, 403}:
                        raise RuntimeError("鉴权失败：请检查 MINERU_API_KEY 是否正确、是否过期。")
                    if response.status_code == 404:
                        raise RuntimeError(
                            f"批量任务不存在（404）：batch_id={batch_id}。"
                            "通常是 batch_id 写错或服务端未保留该任务。"
                        )
                    response.raise_for_status()

                    result = response.json()
                    if result.get("code") != 0:
                        raise RuntimeError(f"获取批量结果失败：{result.get('msg', 'Unknown error')}")

                    items = self._normalize_batch_items(result.get("data"))
                    chosen = self._choose_batch_item(items, data_id=data_id)

                    extracted_pages, total_pages = self._read_extract_progress_pages(chosen.raw)
                    if total_pages and total_pages > 0:
                        progress.update(task, total=total_pages)
                    if extracted_pages is not None:
                        progress.update(task, completed=max(0, extracted_pages))

                    progress.update(task, description=f"MinerU 解析中（{chosen.state}）")

                    if chosen.state in {"pending", "running", "converting", "processing"}:
                        time.sleep(self.config.poll_interval)
                        continue

                    if chosen.state in {"failed", "error"}:
                        raise RuntimeError(f"解析失败：{chosen.err_msg or 'Unknown error'}")

                    if chosen.state in {"done", "completed"}:
                        if total_pages and total_pages > 0:
                            progress.update(task, completed=total_pages)
                        # 统一为 done
                        return _MinerUBatchItem(
                            state="done",
                            full_zip_url=chosen.full_zip_url,
                            err_msg=chosen.err_msg,
                            data_id=chosen.data_id,
                            task_id=chosen.task_id,
                            raw=chosen.raw,
                        )

                    raise RuntimeError(f"未知任务状态：{chosen.state}")

                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                    # 网络抖动：按轮询策略重试
                    time.sleep(self.config.poll_interval)
                    continue

        raise RuntimeError(
            f"轮询超时：已尝试 {self.config.max_poll_attempts} 次，"
            f"总等待约 {self.config.max_poll_attempts * self.config.poll_interval}s。"
        )

    def _read_extract_progress_pages(self, raw: Optional[Dict[str, Any]]) -> Tuple[Optional[int], Optional[int]]:
        """从任务详情中读取页级进度。

        不同接口/版本可能存在字段差异，这里做“尽量兼容”的解析：
        - extract_progress.extracted_pages / extract_progress.total_pages
        - progress.extracted_pages / progress.total_pages（兜底）
        """

        if not raw:
            return None, None

        progress_obj = raw.get("extract_progress")
        if not isinstance(progress_obj, dict):
            progress_obj = raw.get("progress")
        if not isinstance(progress_obj, dict):
            return None, None

        def _as_int(value: Any) -> Optional[int]:
            if value is None:
                return None
            if isinstance(value, bool):
                return None
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value) if value.is_integer() else None
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return None
                try:
                    return int(value)
                except ValueError:
                    return None
            return None

        extracted_pages = _as_int(progress_obj.get("extracted_pages"))
        total_pages = _as_int(progress_obj.get("total_pages"))
        return extracted_pages, total_pages

    def _normalize_batch_items(self, data: Any) -> List[_MinerUBatchItem]:
        """把批量结果 data 归一化为列表，尽量兼容不同返回结构。"""

        candidates: List[Dict[str, Any]] = []

        if isinstance(data, list):
            candidates = [x for x in data if isinstance(x, dict)]
        elif isinstance(data, dict):
            # 常见可能结构：{"extract_result":[...]} / {"results":[...]} / {"files":[...]} / {"tasks":[...]}
            for key in ("extract_result", "extract_results", "results", "files", "tasks", "items", "data"):
                value = data.get(key)
                if isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
                    candidates = value
                    break
            else:
                # 退化为“单对象”
                if any(k in data for k in ("state", "status", "full_zip_url", "err_msg")):
                    candidates = [data]

        if not candidates:
            raise RuntimeError("批量结果 data 为空或结构不符合预期，无法解析。")

        items: List[_MinerUBatchItem] = []
        for raw in candidates:
            state = str(raw.get("state") or raw.get("status") or "").strip().lower()
            full_zip_url = raw.get("full_zip_url") or raw.get("zip_url") or raw.get("result_zip_url")
            err_msg = str(raw.get("err_msg") or raw.get("error") or "")
            items.append(
                _MinerUBatchItem(
                    state=state,
                    full_zip_url=full_zip_url,
                    err_msg=err_msg,
                    data_id=raw.get("data_id"),
                    task_id=raw.get("task_id"),
                    raw=raw,
                )
            )
        return items

    def _choose_batch_item(self, items: List[_MinerUBatchItem], data_id: Optional[str]) -> _MinerUBatchItem:
        """从批量结果里挑出本次上传对应的那一项。"""

        if data_id:
            for item in items:
                if item.data_id == data_id:
                    return item
        return items[0]

    def _download_and_read_content_list(self, full_zip_url: str) -> Tuple[List[Dict[str, Any]], Dict[str, bytes]]:
        """下载结果 zip，并读取 *_content_list.json 与其中引用的图片文件。"""

        response = requests.get(full_zip_url, timeout=self.config.timeout)
        response.raise_for_status()

        zip_bytes = response.content
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            content_list_name = self._find_content_list_name(zf.namelist())
            content_list_raw = zf.read(content_list_name).decode("utf-8")
            content_list = json.loads(content_list_raw)
            if not isinstance(content_list, list):
                raise RuntimeError(f"content_list.json 结构异常：期望 list，实际 {type(content_list)}")

            images_by_path: Dict[str, bytes] = {}
            for item in content_list:
                if not isinstance(item, dict):
                    continue
                if item.get("type") != "image":
                    continue
                img_path = item.get("img_path")
                if not img_path or not isinstance(img_path, str):
                    continue
                try:
                    images_by_path[img_path] = zf.read(img_path)
                except KeyError:
                    # 结果里可能缺图（或路径不同），不要直接让整个解析失败
                    continue

        return content_list, images_by_path

    def _find_content_list_name(self, names: Iterable[str]) -> str:
        """在 zip 里定位 *_content_list.json 文件名。"""

        candidates = [n for n in names if n.endswith("_content_list.json")]
        if not candidates:
            # 兜底：某些版本可能直接叫 content_list.json
            candidates = [n for n in names if n.endswith("content_list.json")]
        if not candidates:
            raise RuntimeError("解析结果 zip 中未找到 *_content_list.json。")
        # 通常只有一个；若有多个，取最短路径（更像根目录文件）
        candidates.sort(key=len)
        return candidates[0]

    def _convert_content_list(
        self, content_list: List[Dict[str, Any]], images_by_path: Dict[str, bytes]
    ) -> Tuple[List[Block], List[Dict[str, Any]], int]:
        """把 content_list 转为内部 Block + images，并计算总页数。"""

        blocks: List[Block] = []
        images: List[Dict[str, Any]] = []

        max_page_idx = -1
        image_index = 0

        for idx, item in enumerate(content_list):
            if not isinstance(item, dict):
                continue

            block_type = str(item.get("type") or "text")
            # 页眉页脚属于噪声：直接丢弃（章节标题来自 text + text_level，不受影响）
            if block_type in {"header", "footer", "page_header", "page_footer"}:
                continue
            page_idx = int(item.get("page_idx") or 0)
            max_page_idx = max(max_page_idx, page_idx)

            bbox = item.get("bbox")
            page_number = page_idx + 1  # 内部约定：Block.page 从 1 开始

            if block_type == "text":
                text = str(item.get("text") or "")
                text_level = item.get("text_level")
                if isinstance(text_level, int) and text_level > 0:
                    blocks.append(
                        Block(
                            id=f"block_{idx}",
                            type="header",
                            text=text,
                            level=text_level,
                            page=page_number,
                            bbox=bbox,
                            metadata={"source": "mineru_content_list"},
                        )
                    )
                else:
                    blocks.append(
                        Block(
                            id=f"block_{idx}",
                            type="text",
                            text=text,
                            level=None,
                            page=page_number,
                            bbox=bbox,
                            metadata={"source": "mineru_content_list"},
                        )
                    )
                continue

            if block_type == "table":
                table_text = str(
                    item.get("table_html")
                    or item.get("html")
                    or item.get("text")
                    or ""
                )
                blocks.append(
                    Block(
                        id=f"block_{idx}",
                        type="table",
                        text=table_text,
                        level=None,
                        page=page_number,
                        bbox=bbox,
                        metadata={"source": "mineru_content_list"},
                    )
                )
                continue

            if block_type == "equation":
                equation_text = str(item.get("latex") or item.get("text") or "")
                blocks.append(
                    Block(
                        id=f"block_{idx}",
                        type="equation",
                        text=equation_text,
                        level=None,
                        page=page_number,
                        bbox=bbox,
                        metadata={"source": "mineru_content_list"},
                    )
                )
                continue

            if block_type == "image":
                img_path = item.get("img_path")
                image_bytes = images_by_path.get(img_path) if isinstance(img_path, str) else None

                width = 0
                height = 0
                if image_bytes:
                    try:
                        with Image.open(BytesIO(image_bytes)) as im:
                            width, height = im.size
                    except Exception:
                        width = 0
                        height = 0

                caption = item.get("image_caption")
                footnote = item.get("image_footnote")

                blocks.append(
                    Block(
                        id=f"block_{idx}",
                        type="image",
                        text="",
                        level=None,
                        page=page_number,
                        bbox=bbox,
                        metadata={
                            "source": "mineru_content_list",
                            "img_path": img_path,
                            "image_caption": caption,
                            "image_footnote": footnote,
                        },
                    )
                )

                images.append(
                    {
                        "page": page_number,
                        "index": image_index,
                        "bbox": bbox,
                        "type": "image",
                        "img_path": img_path,
                        "width": width,
                        "height": height,
                        "image_data": image_bytes,
                        "caption": caption,
                        "footnote": footnote,
                    }
                )
                image_index += 1
                continue

            # 其他类型：尽量保底落为 text，避免直接丢失信息
            fallback_text = str(item.get("text") or "")
            blocks.append(
                Block(
                    id=f"block_{idx}",
                    type=block_type,
                    text=fallback_text,
                    level=None,
                    page=page_number,
                    bbox=bbox,
                    metadata={"source": "mineru_content_list", "raw": item},
                )
            )

        total_pages = max_page_idx + 1 if max_page_idx >= 0 else 0
        return blocks, images, total_pages

    def _extract_raw_text(self, blocks: List[Block]) -> str:
        """从 Block 拼出 raw_text（用于后续分片与调试）。"""

        parts: List[str] = []
        for block in blocks:
            if block.type in {"text", "header"} and block.text:
                parts.append(block.text)
        return "\n\n".join(parts)

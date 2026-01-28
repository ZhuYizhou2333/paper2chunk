from io import BytesIO

from PIL import Image

from paper2chunk.config import MinerUConfig
from paper2chunk.core.pdf_parser_new import MinerUParser


def _make_png_bytes(width: int = 2, height: int = 3) -> bytes:
    image = Image.new("RGB", (width, height), (255, 0, 0))
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_find_content_list_name_prefers_content_list_suffix():
    parser = MinerUParser(MinerUConfig(api_key="test"))
    names = [
        "nested/demo_content_list.json",
        "demo_middle.json",
        "demo_model.json",
        "demo_content_list.json",
    ]
    assert parser._find_content_list_name(names) == "demo_content_list.json"


def test_convert_content_list_to_blocks_and_images():
    parser = MinerUParser(MinerUConfig(api_key="test"))

    png_bytes = _make_png_bytes()
    content_list = [
        {
            "type": "header",
            "text": "Running header",
            "bbox": [0, 0, 1000, 50],
            "page_idx": 0,
        },
        {
            "type": "text",
            "text": "Title",
            "text_level": 1,
            "bbox": [1, 2, 3, 4],
            "page_idx": 0,
        },
        {
            "type": "text",
            "text": "Body",
            "bbox": [5, 6, 7, 8],
            "page_idx": 0,
        },
        {
            "type": "image",
            "img_path": "images/a.png",
            "image_caption": ["Fig 1"],
            "image_footnote": [],
            "bbox": [10, 20, 30, 40],
            "page_idx": 1,
        },
        {
            "type": "footer",
            "text": "Page 2",
            "bbox": [0, 950, 1000, 1000],
            "page_idx": 1,
        },
    ]

    blocks, images, total_pages = parser._convert_content_list(
        content_list=content_list, images_by_path={"images/a.png": png_bytes}
    )

    assert total_pages == 2
    assert [b.type for b in blocks] == ["header", "text", "image"]
    assert blocks[0].level == 1
    assert blocks[0].page == 1
    assert blocks[2].page == 2

    assert len(images) == 1
    assert images[0]["width"] == 2
    assert images[0]["height"] == 3
    assert images[0]["image_data"] == png_bytes


def test_read_extract_progress_pages_parses_multiple_types():
    parser = MinerUParser(MinerUConfig(api_key="test"))

    extracted, total = parser._read_extract_progress_pages(
        {"extract_progress": {"extracted_pages": "3", "total_pages": 10}}
    )
    assert (extracted, total) == (3, 10)

    extracted, total = parser._read_extract_progress_pages(
        {"progress": {"extracted_pages": 2.0, "total_pages": 5.0}}
    )
    assert (extracted, total) == (2, 5)

    extracted, total = parser._read_extract_progress_pages({"extract_progress": {}})
    assert (extracted, total) == (None, None)


def test_normalize_batch_items_supports_extract_result_key():
    parser = MinerUParser(MinerUConfig(api_key="test"))
    items = parser._normalize_batch_items(
        {
            "batch_id": "b",
            "extract_result": [
                {
                    "data_id": "example",
                    "state": "done",
                    "err_msg": "",
                    "full_zip_url": "https://example.com/a.zip",
                }
            ],
        }
    )
    assert len(items) == 1
    assert items[0].data_id == "example"
    assert items[0].state == "done"
    assert items[0].full_zip_url == "https://example.com/a.zip"

from paper2chunk.config import LLMConfig
from paper2chunk.core.chart_analyzer import ChartAnalyzer
from paper2chunk.models import Block


def test_inject_image_descriptions_into_blocks_writes_block_text(monkeypatch):
    analyzer = ChartAnalyzer(
        LLMConfig(
            api_key="test",
            model="gpt-4o",
            vision_model="gpt-4o",
        )
    )

    def _fake_describe_image(*args, **kwargs) -> str:
        return "这是一张测试图片，用于验证注入逻辑。"

    monkeypatch.setattr(analyzer, "describe_image", _fake_describe_image)

    blocks = [
        Block(
            id="b1",
            type="image",
            text="",
            level=None,
            page=2,
            bbox=[0, 0, 100, 100],
            metadata={"img_path": "images/a.png", "image_caption": ["Fig 1"], "image_footnote": ["note"]},
        )
    ]
    images = [
        {
            "page": 2,
            "index": 0,
            "bbox": [0, 0, 100, 100],
            "type": "image",
            "img_path": "images/a.png",
            "width": 10,
            "height": 20,
            "image_data": b"fake",
            "caption": ["Fig 1"],
            "footnote": ["note"],
        }
    ]

    analyzer.inject_image_descriptions_into_blocks(
        blocks=blocks,
        images=images,
        document_title="Doc",
        enable_llm=True,
    )

    assert "【图片】" in blocks[0].text
    assert "标题：Fig 1" in blocks[0].text
    assert "脚注：note" in blocks[0].text
    assert "视觉描述：" in blocks[0].text
    assert "测试图片" in blocks[0].text


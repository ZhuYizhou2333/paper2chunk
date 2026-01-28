"""配置加载相关测试"""

from __future__ import annotations

from paper2chunk.config import Config


def test_config_from_env_loads_openai_settings(monkeypatch):
    """验证 Config.from_env 能正确读取 OpenAI 兼容配置。"""
    monkeypatch.setenv("MINERU_API_KEY", "mineru-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com/v1")

    config = Config.from_env()
    assert config.llm.api_key == "sk-test"
    assert config.llm.model == "gpt-test-model"
    assert config.llm.base_url == "https://example.com/v1"


def test_config_from_env_loads_feature_flags(monkeypatch):
    """验证 FeatureConfig 的环境变量开关（包含 metadata injection）。"""
    monkeypatch.setenv("MINERU_API_KEY", "mineru-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    monkeypatch.setenv("ENABLE_CHART_TO_TEXT", "false")
    monkeypatch.setenv("ENABLE_SEMANTIC_ENHANCEMENT", "true")
    monkeypatch.setenv("ENABLE_METADATA_INJECTION", "false")

    config = Config.from_env()
    assert config.features.enable_chart_to_text is False
    assert config.features.enable_semantic_enhancement is True
    assert config.features.enable_metadata_injection is False


"""paper2chunk 配置管理

约定：
- 默认管道（4 层架构）主要使用 token 维度的 `soft_limit` / `hard_limit`
- 传统管道（向后兼容）主要使用字符维度的 `max_chunk_size` / `min_chunk_size` / `overlap_size`

为了兼容两条管道，`ChunkingConfig` 同时包含两套参数。
"""

from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

load_dotenv()


class MinerUConfig(BaseModel):
    """MinerU API 配置"""
    api_key: Optional[str] = Field(default=None, description="MinerU API key")
    timeout: int = Field(default=300, ge=1, description="API timeout in seconds for file upload")
    poll_interval: int = Field(default=5, ge=1, description="Polling interval in seconds for parsing results")
    max_poll_attempts: int = Field(default=60, ge=1, description="Maximum polling attempts (total wait time = poll_interval * max_poll_attempts)")
    api_base_url: str = Field(default="https://mineru.net", description="MinerU API base URL")


class LLMConfig(BaseModel):
    """LLM 配置"""
    provider: str = Field(default="openai", description="LLM provider (openai or anthropic)")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model name")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-opus-20240229", description="Anthropic model name")
    temperature: float = Field(default=0.3, description="Temperature for LLM")
    max_tokens: int = Field(default=4000, description="Max tokens for LLM response")


class ChunkingConfig(BaseModel):
    """分片配置（同时兼容默认管道与传统管道）"""

    # 默认管道（token 维度）
    soft_limit: int = Field(default=800, description="最佳分片大小（token）")
    hard_limit: int = Field(default=2000, description="最大分片大小（token）")

    # 传统管道（字符维度）
    max_chunk_size: int = Field(default=1000, ge=1, description="最大分片大小（字符）")
    min_chunk_size: int = Field(default=100, ge=1, description="最小分片大小（字符）")
    overlap_size: int = Field(default=50, ge=0, description="分片重叠大小（字符）")

    preserve_structure: bool = Field(default=True, description="是否尽量保持文档结构")


class FeatureConfig(BaseModel):
    """功能开关"""
    enable_chart_to_text: bool = Field(default=True, description="Enable chart-to-text conversion")
    enable_semantic_enhancement: bool = Field(default=True, description="Enable semantic enhancement")
    enable_metadata_injection: bool = Field(default=True, description="Enable metadata injection")


class Config(BaseModel):
    """主配置对象"""
    mineru: MinerUConfig = Field(default_factory=MinerUConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    features: FeatureConfig = Field(default_factory=FeatureConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        mineru_config = MinerUConfig(
            api_key=os.getenv("MINERU_API_KEY"),
            timeout=cls._parse_int_env("MINERU_TIMEOUT", 300),
            poll_interval=cls._parse_int_env("MINERU_POLL_INTERVAL", 5),
            max_poll_attempts=cls._parse_int_env("MINERU_MAX_POLL_ATTEMPTS", 60),
            api_base_url=os.getenv("MINERU_API_BASE_URL", "https://mineru.net"),
        )
        
        llm_config = LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
        )
        
        chunking_config = ChunkingConfig(
            # 默认管道（token）
            soft_limit=cls._parse_int_env("CHUNK_SOFT_LIMIT", 800),
            hard_limit=cls._parse_int_env("CHUNK_HARD_LIMIT", 2000),
            # 传统管道（字符）
            max_chunk_size=cls._parse_int_env("MAX_CHUNK_SIZE", 1000),
            min_chunk_size=cls._parse_int_env("MIN_CHUNK_SIZE", 100),
            overlap_size=cls._parse_int_env("OVERLAP_SIZE", 50),
        )
        
        features_config = FeatureConfig(
            enable_chart_to_text=os.getenv("ENABLE_CHART_TO_TEXT", "true").lower() == "true",
            enable_semantic_enhancement=os.getenv("ENABLE_SEMANTIC_ENHANCEMENT", "true").lower() == "true",
        )
        
        return cls(
            mineru=mineru_config,
            llm=llm_config,
            chunking=chunking_config,
            features=features_config,
        )
    
    @staticmethod
    def _parse_int_env(key: str, default: int) -> int:
        """解析整数环境变量（带兜底与告警）
        
        Args:
            key: 环境变量名
            default: 未设置或非法时的默认值
            
        Returns:
            解析后的整数
        """
        value = os.getenv(key)
        if value is None:
            return default
        
        try:
            return int(value)
        except ValueError:
            print(f"Warning: Invalid integer value for {key}='{value}', using default {default}")
            return default

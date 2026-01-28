"""Configuration management for paper2chunk"""

from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

load_dotenv()


class MinerUConfig(BaseModel):
    """MinerU API configuration"""
    api_key: Optional[str] = Field(default=None, description="MinerU API key")
    timeout: int = Field(default=300, ge=1, description="API timeout in seconds for file upload")
    poll_interval: int = Field(default=5, ge=1, description="Polling interval in seconds for parsing results")
    max_poll_attempts: int = Field(default=60, ge=1, description="Maximum polling attempts (total wait time = poll_interval * max_poll_attempts)")
    api_base_url: str = Field(default="https://mineru.net", description="MinerU API base URL")


class LLMConfig(BaseModel):
    """LLM configuration"""
    provider: str = Field(default="openai", description="LLM provider (openai or anthropic)")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model name")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-opus-20240229", description="Anthropic model name")
    temperature: float = Field(default=0.3, description="Temperature for LLM")
    max_tokens: int = Field(default=4000, description="Max tokens for LLM response")


class ChunkingConfig(BaseModel):
    """Chunking configuration"""
    soft_limit: int = Field(default=800, description="Optimal chunk size in tokens")
    hard_limit: int = Field(default=2000, description="Maximum chunk size in tokens")
    preserve_structure: bool = Field(default=True, description="Preserve document structure")


class FeatureConfig(BaseModel):
    """Feature flags"""
    enable_chart_to_text: bool = Field(default=True, description="Enable chart-to-text conversion")
    enable_semantic_enhancement: bool = Field(default=True, description="Enable semantic enhancement")
    enable_metadata_injection: bool = Field(default=True, description="Enable metadata injection")


class Config(BaseModel):
    """Main configuration class"""
    mineru: MinerUConfig = Field(default_factory=MinerUConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    features: FeatureConfig = Field(default_factory=FeatureConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
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
            soft_limit=cls._parse_int_env("CHUNK_SOFT_LIMIT", 800),
            hard_limit=cls._parse_int_env("CHUNK_HARD_LIMIT", 2000),
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
        """Parse integer from environment variable with error handling
        
        Args:
            key: Environment variable key
            default: Default value if not set or invalid
            
        Returns:
            Parsed integer value
        """
        value = os.getenv(key)
        if value is None:
            return default
        
        try:
            return int(value)
        except ValueError:
            print(f"Warning: Invalid integer value for {key}='{value}', using default {default}")
            return default

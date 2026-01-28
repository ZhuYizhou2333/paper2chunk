"""Configuration management for paper2chunk"""

from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

load_dotenv()


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
    max_chunk_size: int = Field(default=1000, description="Maximum chunk size in characters")
    min_chunk_size: int = Field(default=100, description="Minimum chunk size in characters")
    overlap_size: int = Field(default=50, description="Overlap size between chunks")
    preserve_structure: bool = Field(default=True, description="Preserve document structure")


class FeatureConfig(BaseModel):
    """Feature flags"""
    enable_chart_to_text: bool = Field(default=True, description="Enable chart-to-text conversion")
    enable_semantic_enhancement: bool = Field(default=True, description="Enable semantic enhancement")
    enable_metadata_injection: bool = Field(default=True, description="Enable metadata injection")


class Config(BaseModel):
    """Main configuration class"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    features: FeatureConfig = Field(default_factory=FeatureConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        llm_config = LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
        )
        
        chunking_config = ChunkingConfig(
            max_chunk_size=int(os.getenv("MAX_CHUNK_SIZE", "1000")),
            min_chunk_size=int(os.getenv("MIN_CHUNK_SIZE", "100")),
            overlap_size=int(os.getenv("OVERLAP_SIZE", "50")),
        )
        
        features_config = FeatureConfig(
            enable_chart_to_text=os.getenv("ENABLE_CHART_TO_TEXT", "true").lower() == "true",
            enable_semantic_enhancement=os.getenv("ENABLE_SEMANTIC_ENHANCEMENT", "true").lower() == "true",
        )
        
        return cls(
            llm=llm_config,
            chunking=chunking_config,
            features=features_config,
        )

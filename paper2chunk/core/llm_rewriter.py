"""LLM-based rewriter for semantic enhancement"""

from typing import Optional, List
import openai
from anthropic import Anthropic
from paper2chunk.config import LLMConfig
from paper2chunk.models import Chunk


class LLMRewriter:
    """Rewrite content using LLM for semantic enhancement"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        
        if config.provider == "openai":
            if not config.openai_api_key:
                raise ValueError("OpenAI API key is required when using OpenAI provider")
            openai.api_key = config.openai_api_key
            self.client = openai.OpenAI(api_key=config.openai_api_key)
        elif config.provider == "anthropic":
            if not config.anthropic_api_key:
                raise ValueError("Anthropic API key is required when using Anthropic provider")
            self.client = Anthropic(api_key=config.anthropic_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")
    
    def enhance_chunk(self, chunk: Chunk, document_title: str, section_hierarchy: List[str]) -> str:
        """Enhance a chunk with semantic context
        
        Args:
            chunk: The chunk to enhance
            document_title: Title of the document
            section_hierarchy: Hierarchy of sections
            
        Returns:
            Enhanced content with semantic context
        """
        # Build context from metadata
        context = self._build_context(document_title, section_hierarchy, chunk.metadata.publish_date)
        
        prompt = self._build_enhancement_prompt(chunk.content, context)
        
        if self.config.provider == "openai":
            return self._enhance_with_openai(prompt)
        else:
            return self._enhance_with_anthropic(prompt)
    
    def _build_context(self, document_title: str, section_hierarchy: List[str], publish_date: Optional[str]) -> str:
        """Build context string from metadata"""
        context_parts = [f"Document: {document_title}"]
        
        if section_hierarchy:
            context_parts.append(f"Section: {' > '.join(section_hierarchy)}")
        
        if publish_date:
            context_parts.append(f"Date: {publish_date}")
        
        return " | ".join(context_parts)
    
    def _build_enhancement_prompt(self, content: str, context: str) -> str:
        """Build prompt for semantic enhancement"""
        return f"""You are a semantic enhancement expert for RAG systems. Your task is to rewrite the given text to make it more self-contained and semantically rich.

Context: {context}

Original text:
{content}

Instructions:
1. Add semantic context to pronouns and references (e.g., "it" → "[specific entity]")
2. Make implicit information explicit (e.g., "in 2020" → "in [2020]")
3. Add clarifying context from the section hierarchy when relevant
4. Preserve all original information and meaning
5. Use **bold** for key entities and concepts
6. Keep the text concise and readable

Enhanced text:"""
    
    def _enhance_with_openai(self, prompt: str) -> str:
        """Enhance using OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": "You are a semantic enhancement expert for RAG systems."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return ""
    
    def _enhance_with_anthropic(self, prompt: str) -> str:
        """Enhance using Anthropic API"""
        try:
            response = self.client.messages.create(
                model=self.config.anthropic_model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"Error calling Anthropic API: {e}")
            return ""
    
    def extract_entities_and_keywords(self, text: str) -> tuple[List[str], List[str]]:
        """Extract entities and keywords from text using LLM
        
        Returns:
            Tuple of (entities, keywords)
        """
        prompt = f"""Extract key entities and keywords from the following text.

Text:
{text}

Return a JSON object with two arrays:
- "entities": Named entities (people, organizations, locations, concepts)
- "keywords": Important keywords and phrases

Format:
{{
  "entities": ["entity1", "entity2"],
  "keywords": ["keyword1", "keyword2"]
}}
"""
        
        try:
            if self.config.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.config.openai_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=500,
                )
                result = response.choices[0].message.content.strip()
            else:
                response = self.client.messages.create(
                    model=self.config.anthropic_model,
                    max_tokens=500,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                result = response.content[0].text.strip()
            
            # Parse JSON response
            import json
            data = json.loads(result)
            return data.get("entities", []), data.get("keywords", [])
        except Exception as e:
            print(f"Error extracting entities/keywords: {e}")
            return [], []

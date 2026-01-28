"""Logic repair module for LLM-based TOC hierarchy correction"""

import json
from typing import List, Dict, Any
from paper2chunk.models import Block
from paper2chunk.config import LLMConfig


class LogicRepairer:
    """Repair document structure using LLM
    
    This module extracts the "skeleton" (all headers) from MinerU output
    and uses LLM to correct the hierarchy levels (H1, H2, H3, H4) based on:
    - Numbering logic (e.g., 1. vs 1.1)
    - Semantic logic (e.g., 'Introduction' vs 'Background')
    """
    
    def __init__(self, config: LLMConfig):
        """Initialize the logic repairer
        
        Args:
            config: LLM configuration
        """
        self.config = config
        self._init_llm_client()
    
    def _init_llm_client(self):
        """Initialize LLM client based on provider"""
        if self.config.provider == "openai":
            if not self.config.openai_api_key:
                raise ValueError("OpenAI API key is required")
            import openai
            self.client = openai.OpenAI(api_key=self.config.openai_api_key)
            self.model = self.config.openai_model
        elif self.config.provider == "anthropic":
            if not self.config.anthropic_api_key:
                raise ValueError("Anthropic API key is required")
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)
            self.model = self.config.anthropic_model
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")
    
    def repair_hierarchy(self, blocks: List[Block]) -> List[Block]:
        """Repair header hierarchy levels using LLM
        
        Args:
            blocks: List of blocks from MinerU
            
        Returns:
            List of blocks with corrected header levels
        """
        print("Repairing header hierarchy with LLM...")
        
        # Step 1: Extract skeleton (all headers)
        skeleton = self._extract_skeleton(blocks)
        
        if not skeleton:
            print("  ✓ No headers found, skipping hierarchy repair")
            return blocks
        
        # Step 2: Use LLM to repair hierarchy
        corrected_skeleton = self._llm_repair(skeleton)
        
        # Step 3: Write back corrected levels to blocks
        blocks = self._write_back_levels(blocks, corrected_skeleton)
        
        print(f"  ✓ Repaired hierarchy for {len(skeleton)} headers")
        return blocks
    
    def _extract_skeleton(self, blocks: List[Block]) -> List[Dict[str, Any]]:
        """Extract all headers to form skeleton
        
        Args:
            blocks: List of all blocks
            
        Returns:
            List of header information
        """
        skeleton = []
        for block in blocks:
            if block.type == 'header':
                skeleton.append({
                    'id': block.id,
                    'text': block.text,
                    'original_level': block.level,
                })
        return skeleton
    
    def _llm_repair(self, skeleton: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use LLM to repair header levels
        
        Args:
            skeleton: List of header information
            
        Returns:
            List of headers with corrected levels
        """
        # Prepare prompt
        skeleton_text = '\n'.join([
            f"{i+1}. {item['text']}"
            for i, item in enumerate(skeleton)
        ])
        
        prompt = f"""You are analyzing a document's table of contents. The following is a list of headers extracted from a document, but their hierarchy levels (H1, H2, H3, H4) are missing or incorrect.

Please analyze the numbering logic (e.g., "1." vs "1.1" vs "1.1.1") and semantic logic (e.g., "Introduction" is typically H1, "Background" might be H2) to assign the correct Markdown hierarchy level to each header.

Headers:
{skeleton_text}

Rules:
- H1 (level=1): Main chapters or top-level sections (e.g., "1. Introduction", "Chapter 1")
- H2 (level=2): Sections within chapters (e.g., "1.1 Background", "Section A")
- H3 (level=3): Subsections (e.g., "1.1.1 Related Work", "Subsection A.1")
- H4 (level=4): Sub-subsections (e.g., "1.1.1.1 Details")

Return a JSON array with each header's index (0-based) and its corrected level:
[
  {{"index": 0, "level": 1}},
  {{"index": 1, "level": 2}},
  ...
]

JSON:"""

        try:
            if self.config.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a document structure analysis expert. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.config.temperature,
                    max_tokens=2000,
                )
                result_text = response.choices[0].message.content.strip()
            else:  # anthropic
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    temperature=self.config.temperature,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                result_text = response.content[0].text.strip()
            
            # Parse JSON response
            # Extract JSON from markdown code blocks if present
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            corrected_levels = json.loads(result_text)
            
            # Apply corrected levels to skeleton
            for item in corrected_levels:
                idx = item['index']
                level = item['level']
                if 0 <= idx < len(skeleton):
                    skeleton[idx]['corrected_level'] = level
            
            return skeleton
            
        except json.JSONDecodeError as e:
            print(f"  Warning: Failed to parse LLM response as JSON: {e}")
            print("  Using original levels as fallback")
            for item in skeleton:
                item['corrected_level'] = item.get('original_level') or self._infer_level(item['text'])
            return skeleton
        except Exception as e:
            print(f"  Warning: LLM hierarchy repair failed: {type(e).__name__}: {e}")
            print("  Using original levels as fallback")
            for item in skeleton:
                item['corrected_level'] = item.get('original_level') or self._infer_level(item['text'])
            return skeleton
    
    def _infer_level(self, text: str) -> int:
        """Infer header level from text patterns
        
        Args:
            text: Header text
            
        Returns:
            Inferred level (1-4)
        """
        import re
        
        # Pattern matching for common heading formats
        if re.match(r'^(Chapter|第[一二三四五六七八九十\d]+章)', text, re.IGNORECASE):
            return 1
        elif re.match(r'^\d+\.\s', text):  # "1. Introduction"
            return 2
        elif re.match(r'^\d+\.\d+\s', text):  # "1.1 Background"
            return 3
        elif re.match(r'^\d+\.\d+\.\d+\s', text):  # "1.1.1 Details"
            return 4
        else:
            # Default to level 2 for unrecognized patterns
            return 2
    
    def _write_back_levels(
        self,
        blocks: List[Block],
        corrected_skeleton: List[Dict[str, Any]]
    ) -> List[Block]:
        """Write corrected levels back to blocks
        
        Args:
            blocks: Original blocks
            corrected_skeleton: Skeleton with corrected levels
            
        Returns:
            Blocks with updated levels
        """
        # Create mapping from block ID to corrected level
        level_map = {
            item['id']: item.get('corrected_level', item.get('original_level', 1))
            for item in corrected_skeleton
        }
        
        # Update blocks
        updated_blocks = []
        for block in blocks:
            if block.id in level_map:
                # Create new block with updated level
                block_dict = block.model_dump()
                block_dict['level'] = level_map[block.id]
                block = Block(**block_dict)
            updated_blocks.append(block)
        
        return updated_blocks

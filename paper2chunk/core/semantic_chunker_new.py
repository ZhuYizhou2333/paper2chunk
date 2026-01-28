"""Semantic chunking using dual-threshold recursive DFS"""

from typing import List, Optional
import uuid
from paper2chunk.models import TreeNode, Chunk, ChunkMetadata
from paper2chunk.config import ChunkingConfig, LLMConfig


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken
    
    Args:
        text: Text to count tokens in
        
    Returns:
        Number of tokens
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except (ImportError, Exception):
        # Fallback to rough estimation
        return len(text) // 4


class DualThresholdChunker:
    """Chunk documents using dual-threshold recursive DFS
    
    Principle: Structure boundary > Content length
    
    Algorithm: Dual-Threshold Recursive DFS
    - Parameters:
      * Soft_Limit: Optimal chunk size (default 800 tokens)
      * Hard_Limit: Maximum chunk size (default 2000 tokens)
    
    - Execution:
      * Base Case: If node (including descendants) < Soft_Limit
        -> Keep complete structure, don't split
      * Recursive Case: If > Soft_Limit
        -> Merge small siblings
        -> Recursively process large children
      * Edge Case: If leaf node > Hard_Limit
        -> Use LLM to semantically split
    """
    
    def __init__(self, config: ChunkingConfig, llm_config: Optional[LLMConfig] = None):
        """Initialize the chunker
        
        Args:
            config: Chunking configuration
            llm_config: LLM configuration for splitting large chunks
        """
        self.config = config
        self.llm_config = llm_config
        self.chunks = []
        
        # Initialize LLM for edge case handling
        if llm_config:
            self._init_llm_client()
        else:
            self.llm_client = None
    
    def _init_llm_client(self):
        """Initialize LLM client for large chunk splitting"""
        try:
            if self.llm_config.provider == "openai":
                import openai
                self.llm_client = openai.OpenAI(api_key=self.llm_config.openai_api_key)
                self.llm_model = self.llm_config.openai_model
            elif self.llm_config.provider == "anthropic":
                import anthropic
                self.llm_client = anthropic.Anthropic(api_key=self.llm_config.anthropic_api_key)
                self.llm_model = self.llm_config.anthropic_model
        except Exception as e:
            print(f"  Warning: Could not initialize LLM for chunk splitting: {e}")
            self.llm_client = None
    
    def chunk_tree(
        self,
        tree: TreeNode,
        document_title: str,
        publish_date: Optional[str] = None
    ) -> List[Chunk]:
        """Chunk document tree using dual-threshold recursive DFS
        
        Args:
            tree: Document tree (AST)
            document_title: Document title
            publish_date: Publication date
            
        Returns:
            List of semantic chunks
        """
        print("Chunking document with dual-threshold recursive DFS...")
        
        self.chunks = []
        self.document_title = document_title
        self.publish_date = publish_date
        
        # Start recursive DFS from root
        self._recursive_dfs(tree, [])
        
        # Update chunk indices
        for i, chunk in enumerate(self.chunks):
            chunk.metadata.chunk_index = i
            chunk.metadata.total_chunks = len(self.chunks)
        
        print(f"  ✓ Created {len(self.chunks)} semantic chunks")
        return self.chunks
    
    def _recursive_dfs(
        self,
        node: TreeNode,
        section_hierarchy: List[str]
    ):
        """Recursive DFS chunking algorithm
        
        Args:
            node: Current tree node
            section_hierarchy: Current section hierarchy path
        """
        # Update section hierarchy for section nodes
        if node.type == "section" and node.title:
            section_hierarchy = section_hierarchy + [node.title]
        
        # Calculate total tokens in this node and descendants
        total_tokens = node.get_total_tokens()
        
        # Base Case: Small enough to keep as single chunk
        if total_tokens < self.config.soft_limit:
            content = self._collect_content(node)
            if content.strip():
                self._create_chunk(content, section_hierarchy, node.page_numbers)
            return
        
        # Recursive Case: Too large, need to split
        if node.children:
            # Try to merge small siblings and recursively process large ones
            self._process_children(node.children, section_hierarchy)
        else:
            # Edge Case: Leaf node (pure content) still > Soft_Limit
            content = self._collect_content(node)
            if total_tokens > self.config.hard_limit:
                # Use LLM to semantically split
                sub_chunks = self._llm_split_large_content(content, section_hierarchy, node.page_numbers)
                self.chunks.extend(sub_chunks)
            else:
                # Between soft and hard limit, keep as is
                if content.strip():
                    self._create_chunk(content, section_hierarchy, node.page_numbers)
    
    def _process_children(
        self,
        children: List[TreeNode],
        section_hierarchy: List[str]
    ):
        """Process children nodes, merging small ones and recursing on large ones
        
        Args:
            children: List of child nodes
            section_hierarchy: Current section hierarchy
        """
        accumulated_content = []
        accumulated_pages = set()
        
        for child in children:
            child_tokens = child.get_total_tokens()
            
            if child_tokens < self.config.soft_limit:
                # Small child: accumulate it
                content = self._collect_content(child)
                accumulated_content.append(content)
                accumulated_pages.update(child.page_numbers)
                
                # If accumulated content reaches soft limit, create chunk
                accumulated_text = '\n\n'.join(accumulated_content)
                accumulated_tokens = count_tokens(accumulated_text)
                if accumulated_tokens >= self.config.soft_limit:
                    self._create_chunk(
                        accumulated_text,
                        section_hierarchy,
                        sorted(list(accumulated_pages))
                    )
                    accumulated_content = []
                    accumulated_pages = set()
            else:
                # Large child: first flush accumulated content
                if accumulated_content:
                    accumulated_text = '\n\n'.join(accumulated_content)
                    self._create_chunk(
                        accumulated_text,
                        section_hierarchy,
                        sorted(list(accumulated_pages))
                    )
                    accumulated_content = []
                    accumulated_pages = set()
                
                # Then recursively process this large child
                self._recursive_dfs(child, section_hierarchy)
        
        # Flush remaining accumulated content
        if accumulated_content:
            accumulated_text = '\n\n'.join(accumulated_content)
            if accumulated_text.strip():
                self._create_chunk(
                    accumulated_text,
                    section_hierarchy,
                    sorted(list(accumulated_pages))
                )
    
    def _collect_content(self, node: TreeNode) -> str:
        """Collect all content from node and its descendants
        
        Args:
            node: Tree node
            
        Returns:
            Combined content as string
        """
        parts = []
        
        # Add title if section node
        if node.type == "section" and node.title:
            parts.append(f"## {node.title}")
        
        # Add own content
        if node.content:
            parts.append(node.content)
        
        # Recursively add children content
        for child in node.children:
            child_content = self._collect_content(child)
            if child_content:
                parts.append(child_content)
        
        return '\n\n'.join(parts)
    
    def _create_chunk(
        self,
        content: str,
        section_hierarchy: List[str],
        page_numbers: List[int]
    ):
        """Create a chunk and add to list
        
        Args:
            content: Chunk content
            section_hierarchy: Section hierarchy path
            page_numbers: Page numbers
        """
        chunk_id = str(uuid.uuid4())
        
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            document_title=self.document_title,
            section_hierarchy=section_hierarchy,
            page_numbers=page_numbers,
            publish_date=self.publish_date,
            chunk_index=0,  # Will be updated later
            total_chunks=0,  # Will be updated later
        )
        
        chunk = Chunk(
            content=content,
            metadata=metadata,
        )
        
        self.chunks.append(chunk)
    
    def _llm_split_large_content(
        self,
        content: str,
        section_hierarchy: List[str],
        page_numbers: List[int]
    ) -> List[Chunk]:
        """Use LLM to semantically split large content
        
        Args:
            content: Large content to split
            section_hierarchy: Section hierarchy
            page_numbers: Page numbers
            
        Returns:
            List of sub-chunks
        """
        if not self.llm_client:
            # Fallback: simple split by hard limit
            return self._simple_split(content, section_hierarchy, page_numbers)
        
        try:
            prompt = f"""The following text is too long ({count_tokens(content)} tokens) and needs to be split into smaller semantic chunks.

Please split it into 2-3 smaller chunks at natural semantic boundaries (e.g., paragraph breaks, topic changes).
The target size per chunk should be around {self.config.soft_limit} tokens.

Return the split points as character indices in a JSON array. For example: [0, 500, 1000, 1500]
The indices should be in ascending order and cover the entire text length ({len(content)} characters).

Text:
{content[:4000]}...

JSON:"""
            
            if self.llm_config.provider == "openai":
                response = self.llm_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": "You are a text segmentation expert. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=500,
                )
                result_text = response.choices[0].message.content.strip()
            else:  # anthropic
                response = self.llm_client.messages.create(
                    model=self.llm_model,
                    max_tokens=500,
                    temperature=0.1,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                result_text = response.content[0].text.strip()
            
            # Parse split points
            import json
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            split_points = json.loads(result_text)
            
            # Validate split points
            if not isinstance(split_points, list) or len(split_points) < 2:
                raise ValueError("Invalid split points: need at least 2 points")
            
            # Ensure points are in ascending order and within bounds
            split_points = sorted(split_points)
            split_points = [max(0, min(p, len(content))) for p in split_points]
            
            # Ensure we have start and end
            if split_points[0] != 0:
                split_points.insert(0, 0)
            if split_points[-1] != len(content):
                split_points.append(len(content))
            
            # Create sub-chunks
            chunks = []
            for i in range(len(split_points) - 1):
                start = split_points[i]
                end = split_points[i + 1]
                sub_content = content[start:end].strip()
                
                if sub_content:
                    chunk_id = str(uuid.uuid4())
                    metadata = ChunkMetadata(
                        chunk_id=chunk_id,
                        document_title=self.document_title,
                        section_hierarchy=section_hierarchy,
                        page_numbers=page_numbers,
                        publish_date=self.publish_date,
                        chunk_index=0,
                        total_chunks=0,
                    )
                    chunks.append(Chunk(content=sub_content, metadata=metadata))
            
            return chunks if chunks else self._simple_split(content, section_hierarchy, page_numbers)
            
        except Exception as e:
            print(f"  Warning: LLM splitting failed: {e}, using simple split")
            return self._simple_split(content, section_hierarchy, page_numbers)
    
    def _simple_split(
        self,
        content: str,
        section_hierarchy: List[str],
        page_numbers: List[int]
    ) -> List[Chunk]:
        """Simple fallback splitting by hard limit
        
        Args:
            content: Content to split
            section_hierarchy: Section hierarchy
            page_numbers: Page numbers
            
        Returns:
            List of chunks
        """
        chunks = []
        # Split by hard limit (in characters, roughly 4 chars per token)
        chunk_size = self.config.hard_limit * 4
        
        for i in range(0, len(content), chunk_size):
            chunk_content = content[i:i+chunk_size].strip()
            
            if chunk_content:
                chunk_id = str(uuid.uuid4())
                metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    document_title=self.document_title,
                    section_hierarchy=section_hierarchy,
                    page_numbers=page_numbers,
                    publish_date=self.publish_date,
                    chunk_index=0,
                    total_chunks=0,
                )
                chunks.append(Chunk(content=chunk_content, metadata=metadata))
        
        return chunks

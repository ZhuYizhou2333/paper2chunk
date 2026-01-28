"""Tree builder module for constructing document AST (Abstract Syntax Tree)"""

from typing import List
from paper2chunk.models import Block, TreeNode
import uuid


class TreeBuilder:
    """Build document tree (AST) from linear blocks
    
    This module converts a linear list of blocks into a nested tree structure
    using a stack-based construction algorithm.
    
    Algorithm:
    1. Create a Root node
    2. Maintain a Stack, initially containing only Root
    3. For each Block:
       - If Header (Level N):
         * Pop all nodes with Level >= N from stack
         * Create new section node, attach to stack top
         * Push new node to stack
       - If Content (text/table/image):
         * Create content node, attach to stack top
    """
    
    def __init__(self):
        """Initialize the tree builder"""
        pass
    
    def build_tree(self, blocks: List[Block]) -> TreeNode:
        """Build document tree from blocks
        
        Args:
            blocks: List of blocks with corrected hierarchy
            
        Returns:
            Root node of the document tree
        """
        print("Building document tree (AST)...")
        
        # Create root node
        root = TreeNode(
            id="root",
            type="root",
            title="Document Root",
            level=0,
        )
        
        # Stack for tracking current hierarchy
        stack = [root]
        
        # Process each block
        for block in blocks:
            if block.type == 'header' and block.level:
                # This is a section header
                node = self._create_section_node(block)
                
                # Pop stack until we find the parent (level < current level)
                while len(stack) > 1 and stack[-1].level and stack[-1].level >= block.level:
                    stack.pop()
                
                # Attach to current parent
                parent = stack[-1]
                parent.children.append(node)
                
                # Push this node onto stack
                stack.append(node)
                
            else:
                # This is content (text, table, image, equation, etc.)
                node = self._create_content_node(block)
                
                # Attach to current parent (top of stack)
                parent = stack[-1]
                parent.children.append(node)
        
        node_count = self._count_nodes(root)
        print(f"  ✓ Built tree with {node_count} nodes")
        
        return root
    
    def _create_section_node(self, block: Block) -> TreeNode:
        """Create a section node from a header block
        
        Args:
            block: Header block
            
        Returns:
            TreeNode for the section
        """
        return TreeNode(
            id=block.id,
            type="section",
            title=block.text,
            level=block.level,
            page_numbers=[block.page],
        )
    
    def _create_content_node(self, block: Block) -> TreeNode:
        """Create a content node from a content block
        
        Args:
            block: Content block (text, table, image, etc.)
            
        Returns:
            TreeNode for the content
        """
        return TreeNode(
            id=block.id,
            type="content",
            content=block.text,
            page_numbers=[block.page],
        )
    
    def _count_nodes(self, node: TreeNode) -> int:
        """Count total nodes in tree
        
        Args:
            node: Root node
            
        Returns:
            Total number of nodes
        """
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count

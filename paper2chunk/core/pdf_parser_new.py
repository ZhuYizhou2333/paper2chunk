"""PDF Parser module using MinerU (Magic-PDF) API for layout analysis"""

import requests
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from paper2chunk.models import Document, DocumentMetadata, Block
from paper2chunk.config import MinerUConfig


class MinerUParser:
    """Parser for PDF documents using MinerU (Magic-PDF) API
    
    This parser uses MinerU's vision-based layout analysis to extract:
    - Text blocks (正文)
    - Headers (标题)
    - Tables (表格)
    - Images (图片)
    - Equations (公式)
    - And automatically removes headers/footers
    """
    
    def __init__(self, config: MinerUConfig):
        """Initialize the MinerU parser
        
        Args:
            config: MinerU API configuration
        """
        self.config = config
        if not self.config.api_key:
            raise ValueError("MinerU API key is required. Set MINERU_API_KEY in environment.")
    
    def parse(self, pdf_path: str) -> Document:
        """Parse a PDF file using MinerU API
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Document object with parsed blocks
        """
        print(f"Parsing PDF with MinerU: {pdf_path}")
        
        # Call MinerU API
        parsed_result = self._call_mineru_api(pdf_path)
        
        # Extract metadata
        metadata = self._extract_metadata(parsed_result, pdf_path)
        
        # Extract blocks (remove headers/footers)
        blocks = self._extract_blocks(parsed_result)
        
        # Extract raw text
        raw_text = self._extract_raw_text(blocks)
        
        # Extract images
        images = self._extract_images(parsed_result)
        
        document = Document(
            metadata=metadata,
            raw_text=raw_text,
            blocks=blocks,
            images=images,
        )
        
        print(f"  ✓ Parsed {len(blocks)} blocks from {metadata.total_pages} pages")
        return document
    
    def _call_mineru_api(self, pdf_path: str) -> Dict[str, Any]:
        """Call MinerU API to parse PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Parsed JSON result from MinerU
        """
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        # Prepare request
        headers = {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/pdf',
        }
        
        try:
            # Call API
            response = requests.post(
                self.config.api_url,
                headers=headers,
                data=pdf_bytes,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"MinerU API call failed: {e}")
    
    def _extract_metadata(self, parsed_result: Dict[str, Any], pdf_path: str) -> DocumentMetadata:
        """Extract document metadata from MinerU result
        
        Args:
            parsed_result: Parsed result from MinerU
            pdf_path: Path to PDF file
            
        Returns:
            DocumentMetadata object
        """
        metadata_dict = parsed_result.get('metadata', {})
        
        return DocumentMetadata(
            title=metadata_dict.get('title', Path(pdf_path).stem),
            author=metadata_dict.get('author'),
            publish_date=metadata_dict.get('publish_date'),
            source=pdf_path,
            total_pages=parsed_result.get('total_pages', 0),
        )
    
    def _extract_blocks(self, parsed_result: Dict[str, Any]) -> List[Block]:
        """Extract blocks from MinerU result, filtering out headers/footers
        
        Args:
            parsed_result: Parsed result from MinerU
            
        Returns:
            List of Block objects
        """
        blocks = []
        block_list = parsed_result.get('blocks', [])
        
        for idx, block_data in enumerate(block_list):
            block_type = block_data.get('type', 'text')
            
            # Filter out headers and footers
            if block_type in ['page_header', 'page_footer']:
                continue
            
            block = Block(
                id=f"block_{idx}",
                type=block_type,
                text=block_data.get('text', ''),
                level=block_data.get('level'),  # Will be None for non-header blocks
                page=block_data.get('page', 1),
                bbox=block_data.get('bbox'),
                metadata=block_data.get('metadata', {}),
            )
            blocks.append(block)
        
        return blocks
    
    def _extract_raw_text(self, blocks: List[Block]) -> str:
        """Extract raw text from blocks
        
        Args:
            blocks: List of Block objects
            
        Returns:
            Combined text from all text blocks
        """
        text_parts = []
        for block in blocks:
            if block.type in ['text', 'header'] and block.text:
                text_parts.append(block.text)
        
        return '\n\n'.join(text_parts)
    
    def _extract_images(self, parsed_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract images from MinerU result
        
        Args:
            parsed_result: Parsed result from MinerU
            
        Returns:
            List of image metadata
        """
        images = []
        image_list = parsed_result.get('images', [])
        
        for idx, img_data in enumerate(image_list):
            images.append({
                'page': img_data.get('page', 1),
                'index': idx,
                'bbox': img_data.get('bbox'),
                'type': img_data.get('type', 'image'),
                'metadata': img_data.get('metadata', {}),
            })
        
        return images

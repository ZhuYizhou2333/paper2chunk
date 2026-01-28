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
        """Call MinerU API to parse PDF using batch upload API
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Parsed JSON result from MinerU
            
        Raises:
            ValueError: If PDF file is too large
            RuntimeError: If API call fails
        """
        # Check file size (limit to 50MB)
        file_size = Path(pdf_path).stat().st_size
        max_size = 50 * 1024 * 1024  # 50MB
        
        if file_size > max_size:
            raise ValueError(
                f"PDF file too large: {file_size / (1024*1024):.1f}MB. "
                f"Maximum supported size: {max_size / (1024*1024):.0f}MB"
            )
        
        pdf_filename = Path(pdf_path).name
        
        # Step 1: Request upload URL from batch API
        batch_url = f"{self.config.api_base_url}/api/v4/file-urls/batch"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.config.api_key}'
        }
        
        data = {
            "files": [
                {"name": pdf_filename, "data_id": Path(pdf_path).stem}
            ],
            "model_version": "vlm"
        }
        
        try:
            # Request upload URL
            response = requests.post(batch_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") != 0:
                raise RuntimeError(f"Failed to get upload URL: {result.get('msg', 'Unknown error')}")
            
            batch_id = result["data"]["batch_id"]
            upload_urls = result["data"]["file_urls"]
            
            if not upload_urls:
                raise RuntimeError("No upload URL returned from MinerU API")
            
            upload_url = upload_urls[0]
            print(f"  → Got upload URL (batch_id: {batch_id})")
            
            # Step 2: Upload PDF file to the provided URL
            with open(pdf_path, 'rb') as f:
                upload_response = requests.put(upload_url, data=f, timeout=self.config.timeout)
                upload_response.raise_for_status()
            
            print(f"  → PDF uploaded successfully")
            
            # Step 3: Poll for parsing results
            # MinerU automatically submits parsing task after upload
            parsed_result = self._poll_parsing_result(
                batch_id, 
                max_attempts=self.config.max_poll_attempts,
                interval=self.config.poll_interval
            )
            
            return parsed_result
            
        except RuntimeError:
            # Re-raise RuntimeError from polling as-is to preserve context
            raise
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(
                f"MinerU API call failed for '{pdf_path}': "
                f"HTTP {e.response.status_code} - {e.response.text[:200]}"
            )
        except requests.exceptions.Timeout as e:
            raise RuntimeError(
                f"MinerU API request timed out for '{pdf_path}': {e}"
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"MinerU API call failed for '{pdf_path}': {e}")
    
    def _poll_parsing_result(self, batch_id: str, max_attempts: int = 60, interval: int = 5) -> Dict[str, Any]:
        """Poll for parsing result from MinerU
        
        Args:
            batch_id: Batch ID from upload request
            max_attempts: Maximum number of polling attempts (default: 60, total 5 minutes)
            interval: Interval between polls in seconds (default: 5)
            
        Returns:
            Parsed result
            
        Raises:
            RuntimeError: If polling fails or times out
        """
        import time
        
        result_url = f"{self.config.api_base_url}/api/v4/batches/{batch_id}"
        headers = {
            'Authorization': f'Bearer {self.config.api_key}'
        }
        
        print(f"  → Polling for parsing results...")
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(result_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("code") != 0:
                    raise RuntimeError(f"Failed to get parsing result: {result.get('msg', 'Unknown error')}")
                
                batch_data = result.get("data", {})
                status = batch_data.get("status")
                
                if status == "completed":
                    print(f"  ✓ Parsing completed after {(attempt + 1) * interval}s")
                    # Extract the parsed data
                    files = batch_data.get("files", [])
                    if not files:
                        raise RuntimeError("No files returned in completed batch result")
                    
                    file_data = files[0]
                    
                    # Get the actual parsing result
                    if "result" in file_data:
                        return file_data["result"]
                    elif "result_url" in file_data:
                        # Download result from URL
                        try:
                            result_response = requests.get(file_data["result_url"], timeout=30)
                            result_response.raise_for_status()
                            return result_response.json()
                        except requests.exceptions.RequestException as e:
                            raise RuntimeError(f"Failed to download parsing result from result_url: {e}")
                    else:
                        raise RuntimeError("Batch completed but no result or result_url found in file data")
                    
                elif status == "failed":
                    error_msg = batch_data.get("error", "Unknown error")
                    raise RuntimeError(f"Parsing failed: {error_msg}")
                
                elif status in ["pending", "processing"]:
                    # Still processing, wait and retry
                    if attempt < max_attempts - 1:
                        time.sleep(interval)
                        continue
                    else:
                        raise RuntimeError(f"Parsing timeout after {max_attempts * interval}s (status: {status})")
                
                else:
                    raise RuntimeError(f"Unknown batch status: {status}")
                    
            except RuntimeError:
                # Re-raise RuntimeError as-is
                raise
            except requests.exceptions.RequestException as e:
                if attempt < max_attempts - 1:
                    time.sleep(interval)
                    continue
                else:
                    raise RuntimeError(f"Failed to poll parsing result after {max_attempts} attempts: {e}")
        
        # This should not be reached due to loop logic, but just in case
        raise RuntimeError(f"Polling loop exhausted without result")
    
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

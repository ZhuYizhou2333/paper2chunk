"""Chart and image analysis for chart-to-text conversion"""

from typing import Dict, Any, Optional
from paper2chunk.config import LLMConfig
from paper2chunk.core.llm_rewriter import LLMRewriter
import base64
from io import BytesIO


class ChartAnalyzer:
    """Analyze charts and images to generate text descriptions"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.llm = LLMRewriter(config)
    
    def analyze_chart(self, image_data: bytes, context: str = "") -> str:
        """Analyze a chart/image and generate a text description
        
        Args:
            image_data: Raw image data
            context: Context about where the image appears
            
        Returns:
            Text description of the chart/image
        """
        # For now, return a placeholder
        # In a full implementation, this would use vision models
        # like GPT-4V or Claude 3 with vision capabilities
        
        return self._generate_placeholder_description(context)
    
    def _generate_placeholder_description(self, context: str) -> str:
        """Generate a placeholder description"""
        return f"[Chart/Image: A visual element appears here in the context of {context}. " \
               f"Visual analysis requires vision-enabled LLM models.]"
    
    def should_analyze_image(self, image_info: Dict[str, Any]) -> bool:
        """Determine if an image should be analyzed
        
        Args:
            image_info: Image metadata
            
        Returns:
            True if the image should be analyzed
        """
        # Analyze images that are likely charts/figures
        # Skip small images (likely icons) and very large images (likely full-page scans)
        width = image_info.get("width", 0)
        height = image_info.get("height", 0)
        
        if width < 100 or height < 100:
            return False  # Too small
        
        if width > 2000 or height > 2000:
            return False  # Too large
        
        return True
    
    def analyze_images_in_document(self, images: list, document_title: str) -> Dict[str, str]:
        """Analyze all images in a document
        
        Args:
            images: List of image data from document
            document_title: Title of the document
            
        Returns:
            Dictionary mapping image references to descriptions
        """
        descriptions = {}
        
        for img in images:
            if not self.should_analyze_image(img):
                continue
            
            page = img.get("page", 0)
            index = img.get("index", 0)
            image_data = img.get("image_data")
            
            context = f"{document_title} - Page {page}"
            
            try:
                description = self.analyze_chart(image_data, context)
                key = f"page_{page}_img_{index}"
                descriptions[key] = description
            except Exception as e:
                print(f"Error analyzing image on page {page}: {e}")
        
        return descriptions

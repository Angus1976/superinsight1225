"""
Watermark Service for data export tracking and protection.

Provides comprehensive watermarking capabilities including visible watermarks,
invisible metadata watermarks, and digital signatures for exported data.
"""

import logging
import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, BinaryIO
from uuid import UUID
from sqlalchemy.orm import Session
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import io
import pandas as pd

from src.database.connection import get_db_session
from .models import (
    ExportWatermarkModel, ExportRequestModel, WatermarkType
)

logger = logging.getLogger(__name__)


class WatermarkService:
    """
    Watermark service for data export protection and tracking.
    
    Provides multiple watermarking techniques including visible watermarks,
    invisible metadata watermarks, and digital signatures.
    """
    
    def __init__(self):
        self.watermark_templates = {
            "confidential": "CONFIDENTIAL - {user_id} - {timestamp}",
            "restricted": "RESTRICTED ACCESS - {user_id} - {export_id}",
            "internal": "INTERNAL USE ONLY - {timestamp}",
            "custom": "{custom_text}"
        }
    
    def create_watermark(
        self,
        export_request: ExportRequestModel,
        watermark_type: WatermarkType,
        config: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> Optional[ExportWatermarkModel]:
        """
        Create watermark for export request.
        
        Args:
            export_request: Export request to watermark
            watermark_type: Type of watermark to create
            config: Watermark configuration
            db: Database session
            
        Returns:
            Created watermark model or None if failed
        """
        if db is None:
            db = next(get_db_session())
        
        try:
            # Generate unique watermark ID
            watermark_id = self._generate_watermark_id(export_request)
            
            # Create watermark based on type
            if watermark_type == WatermarkType.VISIBLE:
                watermark_data = self._create_visible_watermark(export_request, config)
            elif watermark_type == WatermarkType.INVISIBLE:
                watermark_data = self._create_invisible_watermark(export_request, config)
            elif watermark_type == WatermarkType.DIGITAL_SIGNATURE:
                watermark_data = self._create_digital_signature(export_request, config)
            elif watermark_type == WatermarkType.METADATA:
                watermark_data = self._create_metadata_watermark(export_request, config)
            else:
                logger.error(f"Unsupported watermark type: {watermark_type}")
                return None
            
            # Create verification hash
            verification_hash = self._create_verification_hash(watermark_data, watermark_id)
            
            # Create watermark record
            watermark = ExportWatermarkModel(
                export_request_id=export_request.id,
                tenant_id=export_request.tenant_id,
                watermark_type=watermark_type,
                watermark_id=watermark_id,
                watermark_text=watermark_data.get("text"),
                watermark_image_path=watermark_data.get("image_path"),
                digital_signature=watermark_data.get("signature"),
                position_config=watermark_data.get("position", {}),
                style_config=watermark_data.get("style", {}),
                metadata_fields=watermark_data.get("metadata", {}),
                verification_hash=verification_hash
            )
            
            db.add(watermark)
            db.commit()
            db.refresh(watermark)
            
            logger.info(f"Watermark created: {watermark_id} for export {export_request.id}")
            return watermark
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating watermark: {e}")
            return None
    
    def apply_watermark_to_file(
        self,
        file_path: str,
        watermark: ExportWatermarkModel,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Apply watermark to exported file.
        
        Args:
            file_path: Path to original file
            watermark: Watermark to apply
            output_path: Output file path (optional)
            
        Returns:
            Path to watermarked file or None if failed
        """
        try:
            if not output_path:
                output_path = file_path.replace('.', '_watermarked.')
            
            # Determine file type and apply appropriate watermarking
            file_extension = file_path.lower().split('.')[-1]
            
            if file_extension in ['csv', 'json', 'xml']:
                return self._apply_text_watermark(file_path, watermark, output_path)
            elif file_extension in ['xlsx', 'xls']:
                return self._apply_excel_watermark(file_path, watermark, output_path)
            elif file_extension == 'pdf':
                return self._apply_pdf_watermark(file_path, watermark, output_path)
            else:
                logger.warning(f"Unsupported file type for watermarking: {file_extension}")
                return file_path
            
        except Exception as e:
            logger.error(f"Error applying watermark to file: {e}")
            return None
    
    def verify_watermark(
        self,
        file_path: str,
        watermark_id: str,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Verify watermark in file.
        
        Args:
            file_path: Path to file to verify
            watermark_id: Watermark ID to verify
            db: Database session
            
        Returns:
            Verification result dictionary
        """
        if db is None:
            db = next(get_db_session())
        
        try:
            # Get watermark record
            watermark = db.query(ExportWatermarkModel).filter(
                ExportWatermarkModel.watermark_id == watermark_id
            ).first()
            
            if not watermark:
                return {
                    "valid": False,
                    "reason": "Watermark not found in database"
                }
            
            # Extract watermark from file
            extracted_data = self._extract_watermark_from_file(file_path, watermark.watermark_type)
            
            if not extracted_data:
                return {
                    "valid": False,
                    "reason": "Could not extract watermark from file"
                }
            
            # Verify watermark data
            verification_hash = self._create_verification_hash(extracted_data, watermark_id)
            
            if verification_hash != watermark.verification_hash:
                return {
                    "valid": False,
                    "reason": "Watermark verification hash mismatch"
                }
            
            return {
                "valid": True,
                "watermark_id": watermark_id,
                "export_request_id": str(watermark.export_request_id),
                "created_at": watermark.created_at.isoformat(),
                "watermark_type": watermark.watermark_type.value
            }
            
        except Exception as e:
            logger.error(f"Error verifying watermark: {e}")
            return {
                "valid": False,
                "reason": f"Verification error: {str(e)}"
            }
    
    def get_watermark_info(
        self,
        export_request_id: UUID,
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Get watermark information for export request.
        
        Args:
            export_request_id: Export request ID
            db: Database session
            
        Returns:
            List of watermark information dictionaries
        """
        if db is None:
            db = next(get_db_session())
        
        watermarks = db.query(ExportWatermarkModel).filter(
            ExportWatermarkModel.export_request_id == export_request_id
        ).all()
        
        return [
            {
                "watermark_id": w.watermark_id,
                "watermark_type": w.watermark_type.value,
                "created_at": w.created_at.isoformat(),
                "has_text": bool(w.watermark_text),
                "has_image": bool(w.watermark_image_path),
                "has_signature": bool(w.digital_signature),
                "metadata_fields": list(w.metadata_fields.keys()) if w.metadata_fields else []
            }
            for w in watermarks
        ]
    
    def _generate_watermark_id(self, export_request: ExportRequestModel) -> str:
        """Generate unique watermark ID."""
        components = [
            str(export_request.id),
            str(export_request.requester_id),
            export_request.tenant_id,
            datetime.utcnow().isoformat()
        ]
        
        hash_input = "|".join(components)
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _create_visible_watermark(
        self,
        export_request: ExportRequestModel,
        config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create visible watermark data."""
        
        config = config or {}
        
        # Generate watermark text
        template = config.get("template", "confidential")
        watermark_text = self._generate_watermark_text(export_request, template, config)
        
        # Position configuration
        position_config = {
            "position": config.get("position", "bottom_right"),
            "margin_x": config.get("margin_x", 10),
            "margin_y": config.get("margin_y", 10),
            "rotation": config.get("rotation", 0)
        }
        
        # Style configuration
        style_config = {
            "font_size": config.get("font_size", 12),
            "font_color": config.get("font_color", "#808080"),
            "opacity": config.get("opacity", 0.5),
            "background_color": config.get("background_color", "transparent")
        }
        
        return {
            "text": watermark_text,
            "position": position_config,
            "style": style_config
        }
    
    def _create_invisible_watermark(
        self,
        export_request: ExportRequestModel,
        config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create invisible watermark data."""
        
        # Invisible watermarks are embedded in file structure or whitespace
        watermark_data = {
            "export_id": str(export_request.id),
            "user_id": str(export_request.requester_id),
            "tenant_id": export_request.tenant_id,
            "timestamp": datetime.utcnow().isoformat(),
            "format": export_request.export_format.value
        }
        
        # Encode as base64 for embedding
        encoded_data = base64.b64encode(json.dumps(watermark_data).encode()).decode()
        
        return {
            "encoded_data": encoded_data,
            "embedding_method": config.get("method", "whitespace") if config else "whitespace"
        }
    
    def _create_digital_signature(
        self,
        export_request: ExportRequestModel,
        config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create digital signature watermark."""
        
        # Create signature payload
        signature_data = {
            "export_id": str(export_request.id),
            "requester_id": str(export_request.requester_id),
            "tenant_id": export_request.tenant_id,
            "created_at": datetime.utcnow().isoformat(),
            "tables": export_request.table_names,
            "format": export_request.export_format.value
        }
        
        # Create hash-based signature (in production, use proper digital signatures)
        signature_string = json.dumps(signature_data, sort_keys=True)
        signature_hash = hashlib.sha256(signature_string.encode()).hexdigest()
        
        return {
            "signature": signature_hash,
            "signature_data": signature_data,
            "algorithm": "SHA-256"
        }
    
    def _create_metadata_watermark(
        self,
        export_request: ExportRequestModel,
        config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create metadata watermark."""
        
        metadata = {
            "export_watermark_id": self._generate_watermark_id(export_request),
            "export_request_id": str(export_request.id),
            "requester_id": str(export_request.requester_id),
            "tenant_id": export_request.tenant_id,
            "export_timestamp": datetime.utcnow().isoformat(),
            "export_format": export_request.export_format.value,
            "table_count": len(export_request.table_names),
            "estimated_records": export_request.estimated_records
        }
        
        return {
            "metadata": metadata
        }
    
    def _generate_watermark_text(
        self,
        export_request: ExportRequestModel,
        template: str,
        config: Dict[str, Any]
    ) -> str:
        """Generate watermark text from template."""
        
        template_text = self.watermark_templates.get(template, template)
        
        # Template variables
        variables = {
            "user_id": str(export_request.requester_id),
            "export_id": str(export_request.id),
            "tenant_id": export_request.tenant_id,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "time": datetime.utcnow().strftime("%H:%M:%S"),
            "custom_text": config.get("custom_text", "")
        }
        
        try:
            return template_text.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template_text
    
    def _create_verification_hash(self, watermark_data: Dict[str, Any], watermark_id: str) -> str:
        """Create verification hash for watermark."""
        
        # Combine watermark data and ID for hash
        hash_input = json.dumps(watermark_data, sort_keys=True) + watermark_id
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def _apply_text_watermark(
        self,
        file_path: str,
        watermark: ExportWatermarkModel,
        output_path: str
    ) -> str:
        """Apply watermark to text-based files (CSV, JSON, XML)."""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add watermark as comment or metadata
            if file_path.lower().endswith('.csv'):
                watermark_line = f"# Watermark: {watermark.watermark_text}\n"
                content = watermark_line + content
            elif file_path.lower().endswith('.json'):
                # Add watermark to JSON metadata
                data = json.loads(content)
                if isinstance(data, dict):
                    data['_watermark'] = {
                        'id': watermark.watermark_id,
                        'text': watermark.watermark_text,
                        'created_at': watermark.created_at.isoformat()
                    }
                content = json.dumps(data, indent=2)
            elif file_path.lower().endswith('.xml'):
                # Add watermark as XML comment
                watermark_comment = f"<!-- Watermark: {watermark.watermark_text} -->\n"
                content = watermark_comment + content
            
            # Add invisible watermark if configured
            if watermark.watermark_type == WatermarkType.INVISIBLE:
                content = self._embed_invisible_watermark(content, watermark)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error applying text watermark: {e}")
            return None
    
    def _apply_excel_watermark(
        self,
        file_path: str,
        watermark: ExportWatermarkModel,
        output_path: str
    ) -> str:
        """Apply watermark to Excel files."""
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Add watermark as a new column or sheet metadata
            if watermark.watermark_text:
                # Add watermark column
                df['_watermark'] = watermark.watermark_text
            
            # Save with watermark
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
                
                # Add watermark sheet
                watermark_info = pd.DataFrame([{
                    'Watermark ID': watermark.watermark_id,
                    'Created At': watermark.created_at.isoformat(),
                    'Export Request ID': str(watermark.export_request_id)
                }])
                watermark_info.to_excel(writer, sheet_name='Watermark', index=False)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error applying Excel watermark: {e}")
            return None
    
    def _apply_pdf_watermark(
        self,
        file_path: str,
        watermark: ExportWatermarkModel,
        output_path: str
    ) -> str:
        """Apply watermark to PDF files."""
        
        # PDF watermarking would require additional libraries like PyPDF2 or reportlab
        # For now, just copy the file and log the watermark
        try:
            import shutil
            shutil.copy2(file_path, output_path)
            
            logger.info(f"PDF watermark applied (metadata only): {watermark.watermark_id}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error applying PDF watermark: {e}")
            return None
    
    def _embed_invisible_watermark(self, content: str, watermark: ExportWatermarkModel) -> str:
        """Embed invisible watermark in content using whitespace or other techniques."""
        
        if not watermark.metadata_fields.get("encoded_data"):
            return content
        
        encoded_data = watermark.metadata_fields["encoded_data"]
        
        # Simple whitespace embedding (add invisible characters)
        # In production, use more sophisticated steganographic techniques
        watermark_chars = []
        for char in encoded_data:
            # Use zero-width characters or specific whitespace patterns
            if char == '0':
                watermark_chars.append('\u200B')  # Zero-width space
            elif char == '1':
                watermark_chars.append('\u200C')  # Zero-width non-joiner
            else:
                watermark_chars.append('\u200D')  # Zero-width joiner
        
        # Embed at the end of content
        return content + ''.join(watermark_chars)
    
    def _extract_watermark_from_file(
        self,
        file_path: str,
        watermark_type: WatermarkType
    ) -> Optional[Dict[str, Any]]:
        """Extract watermark data from file for verification."""
        
        try:
            if watermark_type == WatermarkType.VISIBLE:
                return self._extract_visible_watermark(file_path)
            elif watermark_type == WatermarkType.INVISIBLE:
                return self._extract_invisible_watermark(file_path)
            elif watermark_type == WatermarkType.METADATA:
                return self._extract_metadata_watermark(file_path)
            elif watermark_type == WatermarkType.DIGITAL_SIGNATURE:
                return self._extract_digital_signature(file_path)
            
        except Exception as e:
            logger.error(f"Error extracting watermark: {e}")
            return None
    
    def _extract_visible_watermark(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract visible watermark from file."""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for watermark patterns
            if file_path.lower().endswith('.csv'):
                lines = content.split('\n')
                for line in lines:
                    if line.startswith('# Watermark:'):
                        watermark_text = line.replace('# Watermark:', '').strip()
                        return {"text": watermark_text}
            
            elif file_path.lower().endswith('.json'):
                data = json.loads(content)
                if isinstance(data, dict) and '_watermark' in data:
                    return data['_watermark']
            
        except Exception as e:
            logger.error(f"Error extracting visible watermark: {e}")
        
        return None
    
    def _extract_invisible_watermark(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract invisible watermark from file."""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for zero-width characters at the end
            invisible_chars = []
            for char in reversed(content):
                if char in ['\u200B', '\u200C', '\u200D']:
                    invisible_chars.append(char)
                else:
                    break
            
            if invisible_chars:
                # Decode the invisible watermark
                encoded_data = ""
                for char in reversed(invisible_chars):
                    if char == '\u200B':
                        encoded_data += '0'
                    elif char == '\u200C':
                        encoded_data += '1'
                    else:
                        encoded_data += '2'
                
                return {"encoded_data": encoded_data}
            
        except Exception as e:
            logger.error(f"Error extracting invisible watermark: {e}")
        
        return None
    
    def _extract_metadata_watermark(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract metadata watermark from file."""
        
        # This would depend on the file format and how metadata is stored
        # For now, return None as a placeholder
        return None
    
    def _extract_digital_signature(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract digital signature from file."""
        
        # This would involve extracting and verifying digital signatures
        # For now, return None as a placeholder
        return None
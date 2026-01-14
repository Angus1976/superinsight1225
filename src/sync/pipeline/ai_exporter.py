"""
AI Friendly Exporter for Data Sync Pipeline.

Exports data in formats optimized for AI/ML processing.
"""

import csv
import io
import json
import random
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.sync.pipeline.enums import ExportFormat
from src.sync.pipeline.schemas import (
    ExportConfig,
    ExportedFile,
    ExportResult,
    FieldStats,
    RefineConfig,
    RefinementResult,
    SplitConfig,
    StatisticsReport,
)


class AIFriendlyExporter:
    """
    AI Friendly Exporter for data export.
    
    Features:
    - Multiple export formats (JSON, CSV, JSONL, COCO, Pascal VOC)
    - Data splitting (train/val/test)
    - Semantic enrichment
    - Data desensitization
    - Incremental export
    - Statistics reporting
    """
    
    def __init__(self, semantic_refiner=None, desensitizer=None, export_dir: str = "exports"):
        """
        Initialize the AI Friendly Exporter.
        
        Args:
            semantic_refiner: SemanticRefiner for semantic enrichment
            desensitizer: Desensitizer for data privacy
            export_dir: Directory for exported files
        """
        self.semantic_refiner = semantic_refiner
        self.desensitizer = desensitizer
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self._last_export_checkpoint: Dict[str, Any] = {}
    
    async def export(
        self,
        data: List[Dict[str, Any]],
        format: ExportFormat,
        config: ExportConfig
    ) -> ExportResult:
        """
        Export data in the specified format.
        
        Args:
            data: Data to export
            format: Export format
            config: Export configuration
            
        Returns:
            ExportResult with exported files and statistics
        """
        start_time = time.time()
        export_id = str(uuid.uuid4())[:8]
        
        # Semantic enrichment
        refinement = None
        if config.include_semantics and self.semantic_refiner:
            refinement = await self.semantic_refiner.refine(data, RefineConfig())
            data = self._enrich_with_semantics(data, refinement)
        
        # Data desensitization
        if config.desensitize and self.desensitizer:
            data = await self.desensitizer.desensitize(data)
        
        # Data splitting
        if config.split_config:
            splits = self.split_data(data, config.split_config)
        else:
            splits = {"all": data}
        
        # Export each split
        exported_files = await self._export_splits(splits, format, export_id)
        
        # Generate statistics
        duration_ms = (time.time() - start_time) * 1000
        statistics = self.generate_statistics_report(data, exported_files, duration_ms)
        
        return ExportResult(
            export_id=export_id,
            files=exported_files,
            statistics=statistics,
            format=format,
            success=True
        )

    async def export_incremental(
        self,
        source_id: str,
        data: List[Dict[str, Any]],
        format: ExportFormat,
        config: ExportConfig,
        checkpoint_field: str = "id"
    ) -> ExportResult:
        """
        Export data incrementally based on checkpoint.
        
        Args:
            source_id: Source identifier
            data: Full data set
            format: Export format
            config: Export configuration
            checkpoint_field: Field to use for checkpoint
            
        Returns:
            ExportResult with only new data exported
        """
        # Get last checkpoint
        last_checkpoint = self._last_export_checkpoint.get(source_id)
        
        # Filter to only new data
        if last_checkpoint is not None:
            new_data = [
                record for record in data
                if record.get(checkpoint_field, 0) > last_checkpoint
            ]
        else:
            new_data = data
        
        # Export new data
        result = await self.export(new_data, format, config)
        
        # Update checkpoint
        if new_data:
            max_value = max(
                record.get(checkpoint_field, 0) for record in new_data
            )
            self._last_export_checkpoint[source_id] = max_value
        
        return result
    
    def split_data(
        self,
        data: List[Dict[str, Any]],
        config: SplitConfig
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Split data into train/val/test sets.
        
        Args:
            data: Data to split
            config: Split configuration
            
        Returns:
            Dictionary with split names as keys and data lists as values
        """
        if not data:
            return {"train": [], "val": [], "test": []}
        
        # Normalize ratios
        total_ratio = config.train_ratio + config.val_ratio + config.test_ratio
        if total_ratio == 0:
            return {"train": data, "val": [], "test": []}
        
        train_ratio = config.train_ratio / total_ratio
        val_ratio = config.val_ratio / total_ratio
        # test_ratio is implicit (1 - train - val)
        
        # Shuffle if requested
        if config.shuffle:
            random.seed(config.seed)
            data = data.copy()
            random.shuffle(data)
        
        # Calculate split indices
        n = len(data)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)
        
        return {
            "train": data[:train_end],
            "val": data[train_end:val_end],
            "test": data[val_end:]
        }
    
    def generate_statistics_report(
        self,
        data: List[Dict[str, Any]],
        files: List[ExportedFile],
        duration_ms: float
    ) -> StatisticsReport:
        """
        Generate statistics report for exported data.
        
        Args:
            data: Original data
            files: Exported files
            duration_ms: Export duration in milliseconds
            
        Returns:
            StatisticsReport with detailed statistics
        """
        # Calculate total size
        total_size = sum(f.size_bytes for f in files)
        
        # Calculate split counts
        split_counts = {}
        for f in files:
            split_counts[f.split_name] = split_counts.get(f.split_name, 0) + f.row_count
        
        # Calculate field statistics
        field_stats = self._calculate_field_statistics(data)
        
        return StatisticsReport(
            total_rows=len(data),
            total_size_bytes=total_size,
            split_counts=split_counts,
            field_statistics=field_stats,
            export_duration_ms=duration_ms
        )
    
    async def _export_splits(
        self,
        splits: Dict[str, List[Dict[str, Any]]],
        format: ExportFormat,
        export_id: str
    ) -> List[ExportedFile]:
        """Export each split to a file."""
        files = []
        
        for split_name, split_data in splits.items():
            if not split_data:
                continue
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = self._get_extension(format)
            filename = f"{export_id}_{split_name}_{timestamp}.{extension}"
            filepath = self.export_dir / filename
            
            # Export based on format
            content = self._format_data(split_data, format)
            
            # Write to file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            files.append(ExportedFile(
                filename=filename,
                filepath=str(filepath),
                format=format,
                split_name=split_name,
                row_count=len(split_data),
                size_bytes=len(content.encode("utf-8"))
            ))
        
        return files
    
    def _format_data(
        self,
        data: List[Dict[str, Any]],
        format: ExportFormat
    ) -> str:
        """Format data according to export format."""
        if format == ExportFormat.JSON:
            return self._to_json(data)
        elif format == ExportFormat.CSV:
            return self._to_csv(data)
        elif format == ExportFormat.JSONL:
            return self._to_jsonl(data)
        elif format == ExportFormat.COCO:
            return self._to_coco(data)
        elif format == ExportFormat.PASCAL_VOC:
            return self._to_pascal_voc(data)
        else:
            return self._to_json(data)
    
    def _to_json(self, data: List[Dict[str, Any]]) -> str:
        """Convert to JSON format."""
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    
    def _to_csv(self, data: List[Dict[str, Any]]) -> str:
        """Convert to CSV format."""
        if not data:
            return ""
        
        output = io.StringIO()
        fieldnames = list(data[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in data:
            # Flatten nested structures
            flat_row = {}
            for key, value in row.items():
                if isinstance(value, (dict, list)):
                    flat_row[key] = json.dumps(value, ensure_ascii=False)
                else:
                    flat_row[key] = value
            writer.writerow(flat_row)
        
        return output.getvalue()
    
    def _to_jsonl(self, data: List[Dict[str, Any]]) -> str:
        """Convert to JSON Lines format."""
        lines = []
        for record in data:
            lines.append(json.dumps(record, ensure_ascii=False, default=str))
        return "\n".join(lines)
    
    def _to_coco(self, data: List[Dict[str, Any]]) -> str:
        """Convert to COCO format for object detection."""
        coco_format = {
            "info": {
                "description": "Exported dataset",
                "version": "1.0",
                "year": datetime.now().year,
                "date_created": datetime.now().isoformat()
            },
            "licenses": [],
            "images": [],
            "annotations": [],
            "categories": []
        }
        
        # Extract categories from data
        categories_set = set()
        for idx, record in enumerate(data):
            # Add image entry
            image_entry = {
                "id": idx,
                "file_name": record.get("file_name", f"image_{idx}.jpg"),
                "width": record.get("width", 0),
                "height": record.get("height", 0)
            }
            coco_format["images"].append(image_entry)
            
            # Add annotations if present
            annotations = record.get("annotations", [])
            for ann_idx, ann in enumerate(annotations):
                category = ann.get("category", "unknown")
                categories_set.add(category)
                
                annotation_entry = {
                    "id": len(coco_format["annotations"]),
                    "image_id": idx,
                    "category_id": list(categories_set).index(category),
                    "bbox": ann.get("bbox", [0, 0, 0, 0]),
                    "area": ann.get("area", 0),
                    "iscrowd": ann.get("iscrowd", 0)
                }
                coco_format["annotations"].append(annotation_entry)
        
        # Add categories
        for idx, cat in enumerate(categories_set):
            coco_format["categories"].append({
                "id": idx,
                "name": cat,
                "supercategory": "object"
            })
        
        return json.dumps(coco_format, indent=2, ensure_ascii=False)
    
    def _to_pascal_voc(self, data: List[Dict[str, Any]]) -> str:
        """Convert to Pascal VOC XML format."""
        # For simplicity, return a JSON representation of VOC structure
        # In production, this would generate actual XML files
        voc_data = []
        
        for record in data:
            voc_entry = {
                "annotation": {
                    "folder": "images",
                    "filename": record.get("file_name", "unknown.jpg"),
                    "size": {
                        "width": record.get("width", 0),
                        "height": record.get("height", 0),
                        "depth": record.get("depth", 3)
                    },
                    "objects": []
                }
            }
            
            for ann in record.get("annotations", []):
                obj = {
                    "name": ann.get("category", "unknown"),
                    "bndbox": {
                        "xmin": ann.get("bbox", [0, 0, 0, 0])[0],
                        "ymin": ann.get("bbox", [0, 0, 0, 0])[1],
                        "xmax": ann.get("bbox", [0, 0, 0, 0])[0] + ann.get("bbox", [0, 0, 0, 0])[2],
                        "ymax": ann.get("bbox", [0, 0, 0, 0])[1] + ann.get("bbox", [0, 0, 0, 0])[3]
                    }
                }
                voc_entry["annotation"]["objects"].append(obj)
            
            voc_data.append(voc_entry)
        
        return json.dumps(voc_data, indent=2, ensure_ascii=False)
    
    def _get_extension(self, format: ExportFormat) -> str:
        """Get file extension for format."""
        extensions = {
            ExportFormat.JSON: "json",
            ExportFormat.CSV: "csv",
            ExportFormat.JSONL: "jsonl",
            ExportFormat.COCO: "json",
            ExportFormat.PASCAL_VOC: "json"
        }
        return extensions.get(format, "json")
    
    def _enrich_with_semantics(
        self,
        data: List[Dict[str, Any]],
        refinement: RefinementResult
    ) -> List[Dict[str, Any]]:
        """Enrich data with semantic information."""
        enriched = []
        
        for record in data:
            enriched_record = record.copy()
            enriched_record["_semantics"] = {
                "field_descriptions": refinement.field_descriptions,
                "entities": [e.model_dump() for e in refinement.entities] if refinement.entities else [],
                "relations": [r.model_dump() for r in refinement.relations] if refinement.relations else []
            }
            enriched.append(enriched_record)
        
        return enriched
    
    def _calculate_field_statistics(
        self,
        data: List[Dict[str, Any]]
    ) -> Dict[str, FieldStats]:
        """Calculate statistics for each field."""
        if not data:
            return {}
        
        stats = {}
        sample = data[0]
        
        for field_name in sample.keys():
            values = [record.get(field_name) for record in data]
            non_null = [v for v in values if v is not None]
            
            field_stat = FieldStats(
                field_name=field_name,
                total_count=len(values),
                null_count=len(values) - len(non_null),
                unique_count=len(set(str(v) for v in non_null)),
                data_type=self._infer_type(non_null[0] if non_null else None)
            )
            
            # Add numeric statistics if applicable
            if non_null and isinstance(non_null[0], (int, float)):
                numeric_values = [v for v in non_null if isinstance(v, (int, float))]
                if numeric_values:
                    field_stat.min_value = min(numeric_values)
                    field_stat.max_value = max(numeric_values)
                    field_stat.avg_value = sum(numeric_values) / len(numeric_values)
            
            stats[field_name] = field_stat
        
        return stats
    
    def _infer_type(self, value: Any) -> str:
        """Infer data type from value."""
        if value is None:
            return "unknown"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "unknown"
    
    def get_export_checkpoint(self, source_id: str) -> Optional[Any]:
        """Get the last export checkpoint for a source."""
        return self._last_export_checkpoint.get(source_id)
    
    def clear_export_checkpoint(self, source_id: str) -> None:
        """Clear the export checkpoint for a source."""
        self._last_export_checkpoint.pop(source_id, None)

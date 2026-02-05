"""Annotation Export Service with Metadata.

This module provides comprehensive annotation export functionality:
- Export annotations with full audit metadata
- Support multiple export formats (JSON, CSV, JSONL, XML)
- Include data lineage information
- Support filtered exports
- Maintain export history

Requirements:
- 7.5: Annotation export with metadata
"""

import asyncio
import json
import csv
import io
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field, asdict
from enum import Enum


class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    JSONL = "jsonl"
    CSV = "csv"
    XML = "xml"


class ExportStatus(str, Enum):
    """Export job status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExportFilter:
    """Filter criteria for annotation export."""
    tenant_id: UUID = field(default_factory=uuid4)
    project_id: Optional[UUID] = None
    task_ids: Optional[List[UUID]] = None
    user_ids: Optional[List[UUID]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    annotation_types: Optional[List[str]] = None
    min_confidence: Optional[float] = None
    include_ai_annotations: bool = True
    include_human_annotations: bool = True


@dataclass
class ExportMetadata:
    """Metadata included in export."""
    export_id: UUID = field(default_factory=uuid4)
    export_timestamp: datetime = field(default_factory=datetime.utcnow)
    tenant_id: UUID = field(default_factory=uuid4)
    exported_by: UUID = field(default_factory=uuid4)
    format: ExportFormat = ExportFormat.JSON
    total_annotations: int = 0
    filter_criteria: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"


@dataclass
class AnnotationExportRecord:
    """Single annotation record for export."""
    annotation_id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    project_id: UUID = field(default_factory=uuid4)
    
    # Annotation data
    annotation_type: str = ""
    annotation_data: Dict[str, Any] = field(default_factory=dict)
    
    # Creator info
    created_by: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # AI metadata
    ai_generated: bool = False
    ai_model: Optional[str] = None
    ai_confidence: Optional[float] = None
    
    # Quality metadata
    quality_score: Optional[float] = None
    review_status: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    
    # Lineage
    version_number: int = 1
    parent_annotation_id: Optional[UUID] = None
    source_system: str = "superinsight"


@dataclass
class ExportJob:
    """Export job record."""
    job_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    created_by: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: ExportStatus = ExportStatus.PENDING
    format: ExportFormat = ExportFormat.JSON
    filter: ExportFilter = field(default_factory=ExportFilter)
    total_records: int = 0
    file_size: int = 0
    error_message: Optional[str] = None
    download_url: Optional[str] = None


class AnnotationExportService:
    """Service for exporting annotations with metadata."""

    def __init__(self):
        """Initialize annotation export service."""
        self._annotations: Dict[UUID, AnnotationExportRecord] = {}
        self._export_jobs: Dict[UUID, ExportJob] = {}
        self._lock = asyncio.Lock()
        
        # Indexes
        self._tenant_index: Dict[UUID, List[UUID]] = {}
        self._project_index: Dict[UUID, List[UUID]] = {}
        self._task_index: Dict[UUID, List[UUID]] = {}

    async def add_annotation(
        self,
        annotation: AnnotationExportRecord
    ) -> AnnotationExportRecord:
        """Add an annotation to the export store.

        Args:
            annotation: Annotation record

        Returns:
            Added annotation
        """
        async with self._lock:
            self._annotations[annotation.annotation_id] = annotation
            
            # Update indexes
            tenant_id = annotation.project_id  # Using project_id as tenant proxy
            if tenant_id not in self._tenant_index:
                self._tenant_index[tenant_id] = []
            self._tenant_index[tenant_id].append(annotation.annotation_id)
            
            if annotation.project_id not in self._project_index:
                self._project_index[annotation.project_id] = []
            self._project_index[annotation.project_id].append(annotation.annotation_id)
            
            if annotation.task_id not in self._task_index:
                self._task_index[annotation.task_id] = []
            self._task_index[annotation.task_id].append(annotation.annotation_id)
            
            return annotation

    async def export_annotations(
        self,
        tenant_id: UUID,
        user_id: UUID,
        filter: ExportFilter,
        format: ExportFormat = ExportFormat.JSON,
        include_metadata: bool = True
    ) -> Tuple[str, ExportMetadata]:
        """Export annotations with metadata.

        Args:
            tenant_id: Tenant ID
            user_id: User performing export
            filter: Export filter criteria
            format: Export format
            include_metadata: Include export metadata

        Returns:
            Tuple of (exported data string, export metadata)
        """
        # Get filtered annotations
        annotations = await self._get_filtered_annotations(filter)
        
        # Create export metadata
        metadata = ExportMetadata(
            tenant_id=tenant_id,
            exported_by=user_id,
            format=format,
            total_annotations=len(annotations),
            filter_criteria=self._filter_to_dict(filter)
        )
        
        # Export based on format
        if format == ExportFormat.JSON:
            data = self._export_json(annotations, metadata, include_metadata)
        elif format == ExportFormat.JSONL:
            data = self._export_jsonl(annotations, metadata, include_metadata)
        elif format == ExportFormat.CSV:
            data = self._export_csv(annotations, metadata, include_metadata)
        elif format == ExportFormat.XML:
            data = self._export_xml(annotations, metadata, include_metadata)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return data, metadata

    async def _get_filtered_annotations(
        self,
        filter: ExportFilter
    ) -> List[AnnotationExportRecord]:
        """Get annotations matching filter criteria.

        Args:
            filter: Filter criteria

        Returns:
            List of matching annotations
        """
        async with self._lock:
            results = []
            
            for annotation in self._annotations.values():
                # Apply filters
                if filter.project_id and annotation.project_id != filter.project_id:
                    continue
                
                if filter.task_ids and annotation.task_id not in filter.task_ids:
                    continue
                
                if filter.user_ids and annotation.created_by not in filter.user_ids:
                    continue
                
                if filter.start_date and annotation.created_at < filter.start_date:
                    continue
                
                if filter.end_date and annotation.created_at > filter.end_date:
                    continue
                
                if filter.annotation_types and annotation.annotation_type not in filter.annotation_types:
                    continue
                
                if filter.min_confidence and annotation.ai_confidence:
                    if annotation.ai_confidence < filter.min_confidence:
                        continue
                
                if not filter.include_ai_annotations and annotation.ai_generated:
                    continue
                
                if not filter.include_human_annotations and not annotation.ai_generated:
                    continue
                
                results.append(annotation)
            
            return results

    def _filter_to_dict(self, filter: ExportFilter) -> Dict[str, Any]:
        """Convert filter to dictionary.

        Args:
            filter: Export filter

        Returns:
            Dictionary representation
        """
        return {
            "tenant_id": str(filter.tenant_id),
            "project_id": str(filter.project_id) if filter.project_id else None,
            "task_ids": [str(t) for t in filter.task_ids] if filter.task_ids else None,
            "user_ids": [str(u) for u in filter.user_ids] if filter.user_ids else None,
            "start_date": filter.start_date.isoformat() if filter.start_date else None,
            "end_date": filter.end_date.isoformat() if filter.end_date else None,
            "annotation_types": filter.annotation_types,
            "min_confidence": filter.min_confidence,
            "include_ai_annotations": filter.include_ai_annotations,
            "include_human_annotations": filter.include_human_annotations
        }

    def _annotation_to_dict(self, annotation: AnnotationExportRecord) -> Dict[str, Any]:
        """Convert annotation to dictionary.

        Args:
            annotation: Annotation record

        Returns:
            Dictionary representation
        """
        return {
            "annotation_id": str(annotation.annotation_id),
            "task_id": str(annotation.task_id),
            "project_id": str(annotation.project_id),
            "annotation_type": annotation.annotation_type,
            "annotation_data": annotation.annotation_data,
            "created_by": str(annotation.created_by),
            "created_at": annotation.created_at.isoformat(),
            "updated_at": annotation.updated_at.isoformat() if annotation.updated_at else None,
            "ai_generated": annotation.ai_generated,
            "ai_model": annotation.ai_model,
            "ai_confidence": annotation.ai_confidence,
            "quality_score": annotation.quality_score,
            "review_status": annotation.review_status,
            "reviewed_by": str(annotation.reviewed_by) if annotation.reviewed_by else None,
            "reviewed_at": annotation.reviewed_at.isoformat() if annotation.reviewed_at else None,
            "version_number": annotation.version_number,
            "parent_annotation_id": str(annotation.parent_annotation_id) if annotation.parent_annotation_id else None,
            "source_system": annotation.source_system,
            "lineage": {
                "version": annotation.version_number,
                "parent_id": str(annotation.parent_annotation_id) if annotation.parent_annotation_id else None,
                "source": annotation.source_system
            }
        }

    def _export_json(
        self,
        annotations: List[AnnotationExportRecord],
        metadata: ExportMetadata,
        include_metadata: bool
    ) -> str:
        """Export as JSON.

        Args:
            annotations: Annotations to export
            metadata: Export metadata
            include_metadata: Include metadata in export

        Returns:
            JSON string
        """
        data = {
            "annotations": [self._annotation_to_dict(a) for a in annotations]
        }
        
        if include_metadata:
            data["metadata"] = {
                "export_id": str(metadata.export_id),
                "export_timestamp": metadata.export_timestamp.isoformat(),
                "tenant_id": str(metadata.tenant_id),
                "exported_by": str(metadata.exported_by),
                "format": metadata.format.value,
                "total_annotations": metadata.total_annotations,
                "filter_criteria": metadata.filter_criteria,
                "version": metadata.version
            }
        
        return json.dumps(data, indent=2)

    def _export_jsonl(
        self,
        annotations: List[AnnotationExportRecord],
        metadata: ExportMetadata,
        include_metadata: bool
    ) -> str:
        """Export as JSON Lines.

        Args:
            annotations: Annotations to export
            metadata: Export metadata
            include_metadata: Include metadata in export

        Returns:
            JSONL string
        """
        lines = []
        
        if include_metadata:
            meta_line = {
                "_type": "metadata",
                "export_id": str(metadata.export_id),
                "export_timestamp": metadata.export_timestamp.isoformat(),
                "total_annotations": metadata.total_annotations
            }
            lines.append(json.dumps(meta_line))
        
        for annotation in annotations:
            ann_dict = self._annotation_to_dict(annotation)
            ann_dict["_type"] = "annotation"
            lines.append(json.dumps(ann_dict))
        
        return "\n".join(lines)

    def _export_csv(
        self,
        annotations: List[AnnotationExportRecord],
        metadata: ExportMetadata,
        include_metadata: bool
    ) -> str:
        """Export as CSV.

        Args:
            annotations: Annotations to export
            metadata: Export metadata
            include_metadata: Include metadata in export

        Returns:
            CSV string
        """
        output = io.StringIO()
        
        # Define columns
        columns = [
            "annotation_id", "task_id", "project_id", "annotation_type",
            "created_by", "created_at", "updated_at",
            "ai_generated", "ai_model", "ai_confidence",
            "quality_score", "review_status", "reviewed_by", "reviewed_at",
            "version_number", "parent_annotation_id", "source_system"
        ]
        
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        
        for annotation in annotations:
            row = {
                "annotation_id": str(annotation.annotation_id),
                "task_id": str(annotation.task_id),
                "project_id": str(annotation.project_id),
                "annotation_type": annotation.annotation_type,
                "created_by": str(annotation.created_by),
                "created_at": annotation.created_at.isoformat(),
                "updated_at": annotation.updated_at.isoformat() if annotation.updated_at else "",
                "ai_generated": str(annotation.ai_generated),
                "ai_model": annotation.ai_model or "",
                "ai_confidence": str(annotation.ai_confidence) if annotation.ai_confidence else "",
                "quality_score": str(annotation.quality_score) if annotation.quality_score else "",
                "review_status": annotation.review_status or "",
                "reviewed_by": str(annotation.reviewed_by) if annotation.reviewed_by else "",
                "reviewed_at": annotation.reviewed_at.isoformat() if annotation.reviewed_at else "",
                "version_number": str(annotation.version_number),
                "parent_annotation_id": str(annotation.parent_annotation_id) if annotation.parent_annotation_id else "",
                "source_system": annotation.source_system
            }
            writer.writerow(row)
        
        return output.getvalue()

    def _export_xml(
        self,
        annotations: List[AnnotationExportRecord],
        metadata: ExportMetadata,
        include_metadata: bool
    ) -> str:
        """Export as XML.

        Args:
            annotations: Annotations to export
            metadata: Export metadata
            include_metadata: Include metadata in export

        Returns:
            XML string
        """
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<export>')
        
        if include_metadata:
            lines.append('  <metadata>')
            lines.append(f'    <export_id>{metadata.export_id}</export_id>')
            lines.append(f'    <export_timestamp>{metadata.export_timestamp.isoformat()}</export_timestamp>')
            lines.append(f'    <tenant_id>{metadata.tenant_id}</tenant_id>')
            lines.append(f'    <total_annotations>{metadata.total_annotations}</total_annotations>')
            lines.append('  </metadata>')
        
        lines.append('  <annotations>')
        
        for annotation in annotations:
            lines.append('    <annotation>')
            lines.append(f'      <annotation_id>{annotation.annotation_id}</annotation_id>')
            lines.append(f'      <task_id>{annotation.task_id}</task_id>')
            lines.append(f'      <project_id>{annotation.project_id}</project_id>')
            lines.append(f'      <annotation_type>{annotation.annotation_type}</annotation_type>')
            lines.append(f'      <created_by>{annotation.created_by}</created_by>')
            lines.append(f'      <created_at>{annotation.created_at.isoformat()}</created_at>')
            lines.append(f'      <ai_generated>{str(annotation.ai_generated).lower()}</ai_generated>')
            if annotation.ai_model:
                lines.append(f'      <ai_model>{annotation.ai_model}</ai_model>')
            if annotation.ai_confidence:
                lines.append(f'      <ai_confidence>{annotation.ai_confidence}</ai_confidence>')
            lines.append(f'      <version_number>{annotation.version_number}</version_number>')
            lines.append(f'      <source_system>{annotation.source_system}</source_system>')
            lines.append('    </annotation>')
        
        lines.append('  </annotations>')
        lines.append('</export>')
        
        return '\n'.join(lines)

    async def create_export_job(
        self,
        tenant_id: UUID,
        user_id: UUID,
        filter: ExportFilter,
        format: ExportFormat = ExportFormat.JSON
    ) -> ExportJob:
        """Create an export job.

        Args:
            tenant_id: Tenant ID
            user_id: User creating the job
            filter: Export filter
            format: Export format

        Returns:
            Created export job
        """
        async with self._lock:
            job = ExportJob(
                tenant_id=tenant_id,
                created_by=user_id,
                format=format,
                filter=filter
            )
            self._export_jobs[job.job_id] = job
            return job

    async def get_export_job(self, job_id: UUID) -> Optional[ExportJob]:
        """Get an export job.

        Args:
            job_id: Job ID

        Returns:
            Export job or None
        """
        async with self._lock:
            return self._export_jobs.get(job_id)

    async def update_export_job(
        self,
        job_id: UUID,
        status: ExportStatus,
        total_records: int = 0,
        file_size: int = 0,
        error_message: Optional[str] = None,
        download_url: Optional[str] = None
    ) -> Optional[ExportJob]:
        """Update an export job.

        Args:
            job_id: Job ID
            status: New status
            total_records: Total records exported
            file_size: File size in bytes
            error_message: Error message if failed
            download_url: Download URL if completed

        Returns:
            Updated job or None
        """
        async with self._lock:
            job = self._export_jobs.get(job_id)
            if not job:
                return None
            
            job.status = status
            job.total_records = total_records
            job.file_size = file_size
            job.error_message = error_message
            job.download_url = download_url
            
            if status in [ExportStatus.COMPLETED, ExportStatus.FAILED]:
                job.completed_at = datetime.utcnow()
            
            return job

    async def list_export_jobs(
        self,
        tenant_id: UUID,
        limit: int = 50
    ) -> List[ExportJob]:
        """List export jobs for a tenant.

        Args:
            tenant_id: Tenant ID
            limit: Maximum jobs to return

        Returns:
            List of export jobs
        """
        async with self._lock:
            jobs = [
                job for job in self._export_jobs.values()
                if job.tenant_id == tenant_id
            ]
            jobs.sort(key=lambda j: j.created_at, reverse=True)
            return jobs[:limit]


# Global instance
_export_service: Optional[AnnotationExportService] = None
_export_lock = asyncio.Lock()


async def get_annotation_export_service() -> AnnotationExportService:
    """Get or create the global annotation export service.

    Returns:
        Annotation export service instance
    """
    global _export_service

    async with _export_lock:
        if _export_service is None:
            _export_service = AnnotationExportService()
        return _export_service


async def reset_annotation_export_service():
    """Reset the global annotation export service (for testing)."""
    global _export_service

    async with _export_lock:
        _export_service = None

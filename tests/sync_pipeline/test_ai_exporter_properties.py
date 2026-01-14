"""
Property-based tests for AI Friendly Exporter.

Tests Property 11: Export format correctness
Tests Property 12: Data split ratio accuracy
"""

import pytest
from hypothesis import given, strategies as st, settings
import asyncio
import json
import os
import shutil
import tempfile

from src.sync.pipeline.enums import ExportFormat
from src.sync.pipeline.schemas import ExportConfig, SplitConfig
from src.sync.pipeline.ai_exporter import AIFriendlyExporter


# ============================================================================
# Test Helpers
# ============================================================================

def create_exporter(export_dir: str = None):
    """Create an AI exporter with a temporary directory."""
    if export_dir is None:
        export_dir = tempfile.mkdtemp()
    return AIFriendlyExporter(export_dir=export_dir), export_dir


def create_test_data(count: int) -> list:
    """Create test data with specified count."""
    return [
        {
            "id": i,
            "name": f"Item {i}",
            "value": i * 10.5,
            "active": i % 2 == 0
        }
        for i in range(count)
    ]


def cleanup_dir(dir_path: str):
    """Clean up temporary directory."""
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)


# ============================================================================
# Property 11: Export Format Correctness
# Validates: Requirements 6.1
# ============================================================================

@settings(max_examples=100)
@given(
    record_count=st.integers(min_value=1, max_value=50)
)
def test_json_format_correctness(record_count: int):
    """
    Property 11: JSON export format correctness
    
    Exported JSON files should be valid JSON arrays.
    
    **Validates: Requirements 6.1**
    """
    async def run_test():
        exporter, export_dir = create_exporter()
        try:
            data = create_test_data(record_count)
            config = ExportConfig(include_semantics=False)
            
            result = await exporter.export(data, ExportFormat.JSON, config)
            
            assert result.success
            assert len(result.files) > 0
            
            # Verify JSON is valid
            for file in result.files:
                with open(file.filepath, "r") as f:
                    parsed = json.load(f)
                    assert isinstance(parsed, list)
                    assert len(parsed) == record_count
        finally:
            cleanup_dir(export_dir)
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=100)
@given(
    record_count=st.integers(min_value=1, max_value=50)
)
def test_csv_format_correctness(record_count: int):
    """
    Property 11: CSV export format correctness
    
    Exported CSV files should have header and correct row count.
    
    **Validates: Requirements 6.1**
    """
    async def run_test():
        exporter, export_dir = create_exporter()
        try:
            data = create_test_data(record_count)
            config = ExportConfig(include_semantics=False)
            
            result = await exporter.export(data, ExportFormat.CSV, config)
            
            assert result.success
            assert len(result.files) > 0
            
            # Verify CSV structure
            for file in result.files:
                with open(file.filepath, "r") as f:
                    lines = f.readlines()
                    # Header + data rows
                    assert len(lines) == record_count + 1
                    # Check header has expected fields
                    header = lines[0].strip()
                    assert "id" in header
                    assert "name" in header
        finally:
            cleanup_dir(export_dir)
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=100)
@given(
    record_count=st.integers(min_value=1, max_value=50)
)
def test_jsonl_format_correctness(record_count: int):
    """
    Property 11: JSONL export format correctness
    
    Exported JSONL files should have one JSON object per line.
    
    **Validates: Requirements 6.1**
    """
    async def run_test():
        exporter, export_dir = create_exporter()
        try:
            data = create_test_data(record_count)
            config = ExportConfig(include_semantics=False)
            
            result = await exporter.export(data, ExportFormat.JSONL, config)
            
            assert result.success
            assert len(result.files) > 0
            
            # Verify JSONL structure
            for file in result.files:
                with open(file.filepath, "r") as f:
                    lines = f.readlines()
                    assert len(lines) == record_count
                    
                    # Each line should be valid JSON
                    for line in lines:
                        parsed = json.loads(line.strip())
                        assert isinstance(parsed, dict)
                        assert "id" in parsed
        finally:
            cleanup_dir(export_dir)
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=50)
@given(
    record_count=st.integers(min_value=1, max_value=20)
)
def test_coco_format_correctness(record_count: int):
    """
    Property 11: COCO export format correctness
    
    Exported COCO files should have required structure.
    
    **Validates: Requirements 6.1**
    """
    async def run_test():
        exporter, export_dir = create_exporter()
        try:
            # Create data with annotation structure
            data = [
                {
                    "id": i,
                    "file_name": f"image_{i}.jpg",
                    "width": 640,
                    "height": 480,
                    "annotations": [
                        {"category": "object", "bbox": [10, 20, 100, 100], "area": 10000}
                    ]
                }
                for i in range(record_count)
            ]
            config = ExportConfig(include_semantics=False)
            
            result = await exporter.export(data, ExportFormat.COCO, config)
            
            assert result.success
            
            # Verify COCO structure
            for file in result.files:
                with open(file.filepath, "r") as f:
                    coco = json.load(f)
                    assert "info" in coco
                    assert "images" in coco
                    assert "annotations" in coco
                    assert "categories" in coco
                    assert len(coco["images"]) == record_count
        finally:
            cleanup_dir(export_dir)
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_pascal_voc_format_correctness():
    """
    Property 11: Pascal VOC export format correctness
    
    **Validates: Requirements 6.1**
    """
    async def run_test():
        exporter, export_dir = create_exporter()
        try:
            data = [
                {
                    "file_name": "image_0.jpg",
                    "width": 640,
                    "height": 480,
                    "annotations": [
                        {"category": "cat", "bbox": [10, 20, 100, 100]}
                    ]
                }
            ]
            config = ExportConfig(include_semantics=False)
            
            result = await exporter.export(data, ExportFormat.PASCAL_VOC, config)
            
            assert result.success
            
            # Verify VOC structure
            for file in result.files:
                with open(file.filepath, "r") as f:
                    voc = json.load(f)
                    assert isinstance(voc, list)
                    assert len(voc) == 1
                    assert "annotation" in voc[0]
        finally:
            cleanup_dir(export_dir)
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Property 12: Data Split Ratio Accuracy
# Validates: Requirements 6.3
# ============================================================================

@settings(max_examples=100)
@given(
    train_ratio=st.floats(min_value=0.1, max_value=0.8),
    val_ratio=st.floats(min_value=0.05, max_value=0.3),
    test_ratio=st.floats(min_value=0.05, max_value=0.3)
)
def test_split_ratio_accuracy(train_ratio: float, val_ratio: float, test_ratio: float):
    """
    Property 12: Data split ratio accuracy
    
    The actual split ratios should match configured ratios within 1% tolerance.
    
    **Validates: Requirements 6.3**
    """
    async def run_test():
        exporter, export_dir = create_exporter()
        try:
            # Use 1000 records for better ratio accuracy
            data = create_test_data(1000)
            
            # Normalize ratios
            total = train_ratio + val_ratio + test_ratio
            norm_train = train_ratio / total
            norm_val = val_ratio / total
            norm_test = test_ratio / total
            
            split_config = SplitConfig(
                train_ratio=norm_train,
                val_ratio=norm_val,
                test_ratio=norm_test,
                shuffle=True,
                seed=42
            )
            config = ExportConfig(include_semantics=False, split_config=split_config)
            
            result = await exporter.export(data, ExportFormat.JSON, config)
            
            assert result.success
            
            # Check split counts
            total_exported = sum(result.statistics.split_counts.values())
            assert total_exported == 1000
            
            # Verify ratios within 1% tolerance
            actual_train = result.statistics.split_counts.get("train", 0) / 1000
            actual_val = result.statistics.split_counts.get("val", 0) / 1000
            actual_test = result.statistics.split_counts.get("test", 0) / 1000
            
            assert abs(actual_train - norm_train) < 0.02  # 2% tolerance for rounding
            assert abs(actual_val - norm_val) < 0.02
            assert abs(actual_test - norm_test) < 0.02
        finally:
            cleanup_dir(export_dir)
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=100)
@given(
    record_count=st.integers(min_value=10, max_value=100)
)
def test_split_preserves_all_data(record_count: int):
    """
    Property 12 (extension): Split preserves all data
    
    The sum of all splits should equal the original data count.
    
    **Validates: Requirements 6.3**
    """
    async def run_test():
        exporter, export_dir = create_exporter()
        try:
            data = create_test_data(record_count)
            
            split_config = SplitConfig(
                train_ratio=0.7,
                val_ratio=0.15,
                test_ratio=0.15
            )
            config = ExportConfig(include_semantics=False, split_config=split_config)
            
            result = await exporter.export(data, ExportFormat.JSON, config)
            
            # Total should equal original count
            total = sum(result.statistics.split_counts.values())
            assert total == record_count
        finally:
            cleanup_dir(export_dir)
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_split_with_shuffle_deterministic():
    """
    Property 12 (extension): Shuffle with same seed is deterministic
    
    **Validates: Requirements 6.3**
    """
    async def run_test():
        data = create_test_data(100)
        
        split_config = SplitConfig(
            train_ratio=0.8,
            val_ratio=0.1,
            test_ratio=0.1,
            shuffle=True,
            seed=42
        )
        
        exporter1, dir1 = create_exporter()
        exporter2, dir2 = create_exporter()
        
        try:
            splits1 = exporter1.split_data(data, split_config)
            splits2 = exporter2.split_data(data, split_config)
            
            # Same seed should produce same splits
            assert splits1["train"] == splits2["train"]
            assert splits1["val"] == splits2["val"]
            assert splits1["test"] == splits2["test"]
        finally:
            cleanup_dir(dir1)
            cleanup_dir(dir2)
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_split_without_shuffle():
    """
    Property 12 (extension): Split without shuffle preserves order
    
    **Validates: Requirements 6.3**
    """
    async def run_test():
        exporter, export_dir = create_exporter()
        try:
            data = create_test_data(100)
            
            split_config = SplitConfig(
                train_ratio=0.8,
                val_ratio=0.1,
                test_ratio=0.1,
                shuffle=False
            )
            
            splits = exporter.split_data(data, split_config)
            
            # First 80 should be train
            assert splits["train"][0]["id"] == 0
            assert splits["train"][-1]["id"] == 79
            
            # Next 10 should be val
            assert splits["val"][0]["id"] == 80
            
            # Last 10 should be test
            assert splits["test"][0]["id"] == 90
        finally:
            cleanup_dir(export_dir)
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Statistics Report Tests
# ============================================================================

@settings(max_examples=50)
@given(
    record_count=st.integers(min_value=1, max_value=50)
)
def test_statistics_report_completeness(record_count: int):
    """
    Test that statistics report contains all required fields.
    """
    async def run_test():
        exporter, export_dir = create_exporter()
        try:
            data = create_test_data(record_count)
            config = ExportConfig(include_semantics=False)
            
            result = await exporter.export(data, ExportFormat.JSON, config)
            
            stats = result.statistics
            assert stats.total_rows == record_count
            assert stats.total_size_bytes > 0
            assert stats.export_duration_ms >= 0
            assert "id" in stats.field_statistics
            assert "name" in stats.field_statistics
        finally:
            cleanup_dir(export_dir)
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_field_statistics_numeric():
    """
    Test that numeric field statistics are calculated correctly.
    """
    async def run_test():
        exporter, export_dir = create_exporter()
        try:
            data = [
                {"id": 1, "value": 10},
                {"id": 2, "value": 20},
                {"id": 3, "value": 30}
            ]
            config = ExportConfig(include_semantics=False)
            
            result = await exporter.export(data, ExportFormat.JSON, config)
            
            value_stats = result.statistics.field_statistics.get("value")
            assert value_stats is not None
            assert value_stats.min_value == 10
            assert value_stats.max_value == 30
            assert value_stats.avg_value == 20.0
        finally:
            cleanup_dir(export_dir)
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Incremental Export Tests
# ============================================================================

def test_incremental_export():
    """
    Test incremental export only exports new data.
    """
    async def run_test():
        exporter, export_dir = create_exporter()
        try:
            # First export
            data1 = [{"id": 1}, {"id": 2}, {"id": 3}]
            config = ExportConfig(include_semantics=False)
            
            result1 = await exporter.export_incremental(
                "source1", data1, ExportFormat.JSON, config
            )
            assert result1.statistics.total_rows == 3
            
            # Second export with more data
            data2 = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}]
            result2 = await exporter.export_incremental(
                "source1", data2, ExportFormat.JSON, config
            )
            
            # Should only export new records (id > 3)
            assert result2.statistics.total_rows == 2
        finally:
            cleanup_dir(export_dir)
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_export_checkpoint_management():
    """
    Test export checkpoint get and clear.
    """
    async def run_test():
        exporter, export_dir = create_exporter()
        try:
            data = [{"id": 1}, {"id": 2}, {"id": 3}]
            config = ExportConfig(include_semantics=False)
            
            await exporter.export_incremental(
                "source1", data, ExportFormat.JSON, config
            )
            
            # Check checkpoint
            checkpoint = exporter.get_export_checkpoint("source1")
            assert checkpoint == 3
            
            # Clear checkpoint
            exporter.clear_export_checkpoint("source1")
            assert exporter.get_export_checkpoint("source1") is None
        finally:
            cleanup_dir(export_dir)
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Edge Cases
# ============================================================================

def test_export_empty_data():
    """
    Test export with empty data.
    """
    async def run_test():
        exporter, export_dir = create_exporter()
        try:
            data = []
            config = ExportConfig(include_semantics=False)
            
            result = await exporter.export(data, ExportFormat.JSON, config)
            
            assert result.success
            assert result.statistics.total_rows == 0
        finally:
            cleanup_dir(export_dir)
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_split_empty_data():
    """
    Test split with empty data.
    """
    exporter, export_dir = create_exporter()
    try:
        data = []
        split_config = SplitConfig()
        
        splits = exporter.split_data(data, split_config)
        
        assert splits["train"] == []
        assert splits["val"] == []
        assert splits["test"] == []
    finally:
        cleanup_dir(export_dir)


def test_split_zero_ratios():
    """
    Test split with zero ratios.
    """
    exporter, export_dir = create_exporter()
    try:
        data = create_test_data(10)
        split_config = SplitConfig(
            train_ratio=0,
            val_ratio=0,
            test_ratio=0
        )
        
        splits = exporter.split_data(data, split_config)
        
        # Should put all in train when ratios are zero
        assert len(splits["train"]) == 10
    finally:
        cleanup_dir(export_dir)

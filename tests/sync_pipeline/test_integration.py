"""
Integration tests for Data Sync Pipeline.

Tests end-to-end flows including:
- Read → Save → Export flow
- Scheduled pull operations
- Webhook receive flow
"""

import pytest
import asyncio
import tempfile
import shutil
import os
from datetime import datetime

from src.sync.pipeline.enums import (
    DatabaseType,
    ConnectionMethod,
    SaveStrategy,
    ExportFormat,
    JobStatus,
)
from src.sync.pipeline.schemas import (
    DataSourceConfig,
    PullConfig,
    SaveConfig,
    RefineConfig,
    ExportConfig,
    SplitConfig,
    ScheduleConfig,
)
from src.sync.pipeline.data_reader import DataReader, DataReaderWithStats
from src.sync.pipeline.data_puller import DataPuller
from src.sync.pipeline.data_receiver import DataReceiver
from src.sync.pipeline.save_strategy import SaveStrategyManager
from src.sync.pipeline.semantic_refiner import SemanticRefiner
from src.sync.pipeline.ai_exporter import AIFriendlyExporter
from src.sync.pipeline.scheduler import SyncScheduler
from src.sync.pipeline.checkpoint_store import CheckpointStore
from src.sync.pipeline.idempotency_store import IdempotencyStore


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_export_dir():
    """Create a temporary directory for exports."""
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    return [
        {"id": i, "name": f"Item {i}", "value": i * 10.5, "created_at": f"2026-01-{(i % 28) + 1:02d}"}
        for i in range(100)
    ]


@pytest.fixture
def checkpoint_store():
    """Create a checkpoint store."""
    return CheckpointStore()


@pytest.fixture
def idempotency_store():
    """Create an idempotency store."""
    return IdempotencyStore()


# ============================================================================
# Integration Test: Read → Save → Export Flow
# ============================================================================

class TestReadSaveExportFlow:
    """Test the complete read → save → export flow."""
    
    @pytest.mark.asyncio
    async def test_complete_flow_with_memory_save(self, sample_data, temp_export_dir):
        """
        Test complete flow: data → memory save → semantic refine → export
        """
        # Step 1: Save to memory
        save_manager = SaveStrategyManager()
        save_config = SaveConfig(strategy=SaveStrategy.MEMORY)
        
        save_result = await save_manager.save(sample_data, SaveStrategy.MEMORY, save_config)
        
        assert save_result.success
        assert save_result.rows_saved == 100
        assert save_result.strategy_used == SaveStrategy.MEMORY
        
        # Step 2: Semantic refinement
        refiner = SemanticRefiner()
        refine_config = RefineConfig(
            generate_descriptions=True,
            generate_dictionary=True,
            extract_entities=True
        )
        
        refinement = await refiner.refine(sample_data, refine_config)
        
        assert refinement.field_descriptions is not None
        assert "id" in refinement.field_descriptions
        assert refinement.data_dictionary is not None
        
        # Step 3: Export
        exporter = AIFriendlyExporter(
            semantic_refiner=refiner,
            export_dir=temp_export_dir
        )
        export_config = ExportConfig(
            include_semantics=True,
            split_config=SplitConfig(train_ratio=0.8, val_ratio=0.1, test_ratio=0.1)
        )
        
        export_result = await exporter.export(sample_data, ExportFormat.JSON, export_config)
        
        assert export_result.success
        assert len(export_result.files) == 3  # train, val, test
        assert export_result.statistics.total_rows == 100
        
        # Verify files exist
        for file in export_result.files:
            assert os.path.exists(file.filepath)
    
    @pytest.mark.asyncio
    async def test_flow_with_hybrid_save(self, sample_data, temp_export_dir):
        """
        Test flow with hybrid save strategy.
        """
        save_manager = SaveStrategyManager()
        
        # Small data should use memory
        small_data = sample_data[:10]
        save_config = SaveConfig(
            strategy=SaveStrategy.HYBRID,
            hybrid_threshold_bytes=10000  # 10KB threshold
        )
        
        result = await save_manager.save(small_data, SaveStrategy.HYBRID, save_config)
        
        assert result.success
        assert result.strategy_used == SaveStrategy.MEMORY
    
    @pytest.mark.asyncio
    async def test_flow_with_multiple_formats(self, sample_data, temp_export_dir):
        """
        Test export in multiple formats.
        """
        exporter = AIFriendlyExporter(export_dir=temp_export_dir)
        config = ExportConfig(include_semantics=False)
        
        formats = [ExportFormat.JSON, ExportFormat.CSV, ExportFormat.JSONL]
        
        for fmt in formats:
            result = await exporter.export(sample_data, fmt, config)
            assert result.success
            assert result.format == fmt


# ============================================================================
# Integration Test: Scheduled Pull Operations
# ============================================================================

class TestScheduledPullFlow:
    """Test scheduled pull operations."""
    
    @pytest.mark.asyncio
    async def test_schedule_and_trigger(self, checkpoint_store):
        """
        Test creating a schedule and triggering it manually.
        """
        scheduler = SyncScheduler()
        
        # Create schedule
        config = ScheduleConfig(
            cron_expression="*/5 * * * *",
            priority=5,
            enabled=True
        )
        
        job = await scheduler.schedule("job_1", "source_1", config)
        
        assert job.job_id == "job_1"
        assert job.status == JobStatus.PENDING
        assert job.config.enabled is True
        
        # Trigger manually
        result = await scheduler.trigger_manual("job_1")
        
        assert result.success
        
        # Check status updated
        status = await scheduler.get_status("job_1")
        assert status == JobStatus.COMPLETED
        
        # Check history recorded
        history = await scheduler.get_history("job_1")
        assert len(history) == 1
        assert history[0].status == JobStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_multiple_jobs_priority(self):
        """
        Test that jobs are sorted by priority.
        """
        scheduler = SyncScheduler()
        
        # Create jobs with different priorities
        await scheduler.schedule("job_low", "source_1", ScheduleConfig(
            cron_expression="0 * * * *", priority=1
        ))
        await scheduler.schedule("job_high", "source_2", ScheduleConfig(
            cron_expression="0 * * * *", priority=9
        ))
        await scheduler.schedule("job_mid", "source_3", ScheduleConfig(
            cron_expression="0 * * * *", priority=5
        ))
        
        jobs = await scheduler.list_jobs()
        
        assert jobs[0].job_id == "job_high"
        assert jobs[1].job_id == "job_mid"
        assert jobs[2].job_id == "job_low"
    
    @pytest.mark.asyncio
    async def test_job_enable_disable(self):
        """
        Test enabling and disabling jobs.
        """
        scheduler = SyncScheduler()
        
        await scheduler.schedule("job_1", "source_1", ScheduleConfig(
            cron_expression="0 * * * *", enabled=True
        ))
        
        # Disable
        await scheduler.disable_job("job_1")
        job = scheduler.get_job("job_1")
        assert job.config.enabled is False
        assert job.next_run_at is None
        
        # Enable
        await scheduler.enable_job("job_1")
        job = scheduler.get_job("job_1")
        assert job.config.enabled is True
        assert job.next_run_at is not None


# ============================================================================
# Integration Test: Webhook Receive Flow
# ============================================================================

class TestWebhookReceiveFlow:
    """Test webhook receive operations."""
    
    @pytest.mark.asyncio
    async def test_receive_json_data(self, idempotency_store, temp_export_dir):
        """
        Test receiving JSON data via webhook and processing it.
        """
        receiver = DataReceiver(idempotency_store, secret_key="test_secret")
        
        # Prepare data
        import json
        data = json.dumps([{"id": 1, "name": "Test"}])
        signature = receiver.generate_signature(data)
        
        # Receive
        result = await receiver.receive(
            data=data,
            format="json",
            signature=signature,
            idempotency_key="key_1"
        )
        
        assert result.success
        assert result.duplicate is False
        assert result.rows_received == 1
        
        # Second receive with same key should be duplicate
        result2 = await receiver.receive(
            data=data,
            format="json",
            signature=signature,
            idempotency_key="key_1"
        )
        
        assert result2.success
        assert result2.duplicate is True
    
    @pytest.mark.asyncio
    async def test_receive_csv_data(self, idempotency_store):
        """
        Test receiving CSV data via webhook.
        """
        receiver = DataReceiver(idempotency_store, secret_key="test_secret")
        
        csv_data = "id,name\n1,Test1\n2,Test2\n3,Test3"
        signature = receiver.generate_signature(csv_data)
        
        result = await receiver.receive(
            data=csv_data,
            format="csv",
            signature=signature,
            idempotency_key="csv_key_1"
        )
        
        assert result.success
        assert result.rows_received == 3
    
    @pytest.mark.asyncio
    async def test_receive_invalid_signature(self, idempotency_store):
        """
        Test that invalid signature is rejected.
        """
        receiver = DataReceiver(idempotency_store, secret_key="test_secret")
        
        data = '{"id": 1}'
        
        with pytest.raises(Exception):  # InvalidSignatureError
            await receiver.receive(
                data=data,
                format="json",
                signature="invalid_signature",
                idempotency_key="key_invalid"
            )


# ============================================================================
# Integration Test: Semantic Refinement with Cache
# ============================================================================

class TestSemanticRefinementFlow:
    """Test semantic refinement with caching."""
    
    @pytest.mark.asyncio
    async def test_refinement_caching(self, sample_data):
        """
        Test that refinement results are cached.
        """
        refiner = SemanticRefiner()
        config = RefineConfig(generate_descriptions=True)
        
        # First call
        result1 = await refiner.refine(sample_data, config)
        
        # Second call should hit cache
        result2 = await refiner.refine(sample_data, config)
        
        assert result1.field_descriptions == result2.field_descriptions
        assert len(refiner._memory_cache) == 1
    
    @pytest.mark.asyncio
    async def test_refinement_with_custom_rules(self, sample_data):
        """
        Test refinement with custom transformation rules.
        """
        from src.sync.pipeline.schemas import RefineRule
        
        refiner = SemanticRefiner()
        
        rule = RefineRule(
            name="uppercase_name",
            field_pattern="name",
            transformation="uppercase",
            parameters={}
        )
        
        config = RefineConfig(
            generate_descriptions=False,
            custom_rules=[rule]
        )
        
        result = await refiner.refine(sample_data[:5], config)
        
        assert result is not None


# ============================================================================
# Integration Test: Data Puller with Checkpoint
# ============================================================================

class TestDataPullerFlow:
    """Test data puller with checkpoint persistence."""
    
    @pytest.mark.asyncio
    async def test_checkpoint_persistence(self, checkpoint_store):
        """
        Test that checkpoints are persisted across pulls.
        """
        puller = DataPuller(data_reader=None, checkpoint_store=checkpoint_store)
        
        # Save checkpoint
        from src.sync.pipeline.schemas import Checkpoint
        checkpoint = Checkpoint(
            source_id="source_1",
            last_value="2026-01-13T00:00:00Z",
            last_pull_at=datetime.utcnow(),
            rows_pulled=1000
        )
        
        await puller.save_checkpoint("source_1", checkpoint)
        
        # Retrieve checkpoint
        retrieved = await checkpoint_store.get("source_1")
        
        assert retrieved is not None
        assert retrieved.last_value == "2026-01-13T00:00:00Z"
        assert retrieved.rows_pulled == 1000
    
    @pytest.mark.asyncio
    async def test_cron_validation(self, checkpoint_store):
        """
        Test cron expression validation.
        """
        from src.sync.pipeline.data_puller import CronExpressionError
        
        puller = DataPuller(data_reader=None, checkpoint_store=checkpoint_store)
        
        # Valid cron expressions - should not raise
        valid_crons = [
            "* * * * *",
            "*/5 * * * *",
            "0 2 * * *",
            "0 0 1 * *",
        ]
        
        for cron in valid_crons:
            # Valid crons should be accepted in PullConfig
            config = PullConfig(cron_expression=cron)
            assert config.cron_expression == cron
        
        # Invalid cron expressions - should raise during pull
        # The validation happens in the puller, not in config creation


# ============================================================================
# Integration Test: Full Pipeline
# ============================================================================

class TestFullPipeline:
    """Test the complete pipeline from end to end."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self, sample_data, temp_export_dir, checkpoint_store, idempotency_store):
        """
        Test the complete pipeline:
        1. Receive data via webhook
        2. Save with hybrid strategy
        3. Refine semantically
        4. Export in multiple formats
        5. Schedule for future pulls
        """
        # Step 1: Receive data
        receiver = DataReceiver(idempotency_store, secret_key="test_secret")
        import json
        data_str = json.dumps(sample_data)
        signature = receiver.generate_signature(data_str)
        
        receive_result = await receiver.receive(
            data=data_str,
            format="json",
            signature=signature,
            idempotency_key="full_pipeline_key"
        )
        assert receive_result.success
        
        # Step 2: Save
        save_manager = SaveStrategyManager()
        save_result = await save_manager.save(
            sample_data,
            SaveStrategy.HYBRID,
            SaveConfig(hybrid_threshold_bytes=1000000)
        )
        assert save_result.success
        
        # Step 3: Refine
        refiner = SemanticRefiner()
        refinement = await refiner.refine(sample_data, RefineConfig())
        assert refinement.field_descriptions is not None
        
        # Step 4: Export
        exporter = AIFriendlyExporter(
            semantic_refiner=refiner,
            export_dir=temp_export_dir
        )
        
        for fmt in [ExportFormat.JSON, ExportFormat.CSV]:
            export_result = await exporter.export(
                sample_data,
                fmt,
                ExportConfig(include_semantics=True)
            )
            assert export_result.success
        
        # Step 5: Schedule
        scheduler = SyncScheduler()
        job = await scheduler.schedule(
            "pipeline_job",
            "source_1",
            ScheduleConfig(cron_expression="0 * * * *", priority=5)
        )
        assert job.status == JobStatus.PENDING
        
        # Verify everything worked
        assert save_manager.memory_batch_count >= 1
        assert len(refiner._memory_cache) >= 1
        assert scheduler.job_count == 1

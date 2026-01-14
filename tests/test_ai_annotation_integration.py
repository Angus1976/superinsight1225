"""
Integration tests for AI Annotation module.

Tests the complete annotation workflow:
- Pre-annotation → Review → Validation
- Third-party tool integration
- Human-AI collaboration scenarios

Task 15.1: 端到端集成测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from uuid import uuid4


# ============================================================================
# Mock Services for Integration Testing
# ============================================================================

class MockPreAnnotationEngine:
    """Mock pre-annotation engine."""
    
    async def pre_annotate(self, tasks: List[Dict], annotation_type: str) -> List[Dict]:
        """Generate pre-annotations for tasks."""
        results = []
        for task in tasks:
            confidence = 0.5 + (hash(task.get("id", "")) % 50) / 100
            results.append({
                "task_id": task.get("id"),
                "annotation_data": {"label": f"predicted_{annotation_type}"},
                "confidence": confidence,
                "method_used": "llm",
            })
        return results


class MockReviewFlowEngine:
    """Mock review flow engine."""
    
    def __init__(self):
        self._tasks = {}
        self._history = {}
    
    async def submit_for_review(self, annotation_id: str, annotator_id: str) -> Dict:
        """Submit annotation for review."""
        task_id = str(uuid4())
        task = {
            "id": task_id,
            "annotation_id": annotation_id,
            "annotator_id": annotator_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }
        self._tasks[task_id] = task
        self._history[annotation_id] = [{"action": "submit", "timestamp": datetime.utcnow().isoformat()}]
        return task
    
    async def approve(self, task_id: str, reviewer_id: str, comments: str = "") -> Dict:
        """Approve annotation."""
        task = self._tasks.get(task_id)
        if not task:
            return {"success": False, "message": "Task not found"}
        
        task["status"] = "approved"
        task["reviewer_id"] = reviewer_id
        task["completed_at"] = datetime.utcnow().isoformat()
        
        self._history[task["annotation_id"]].append({
            "action": "approve",
            "reviewer_id": reviewer_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return {"success": True, "task": task}
    
    async def reject(self, task_id: str, reviewer_id: str, reason: str) -> Dict:
        """Reject annotation."""
        task = self._tasks.get(task_id)
        if not task:
            return {"success": False, "message": "Task not found"}
        
        task["status"] = "rejected"
        task["reviewer_id"] = reviewer_id
        task["rejection_reason"] = reason
        
        self._history[task["annotation_id"]].append({
            "action": "reject",
            "reviewer_id": reviewer_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return {"success": True, "task": task}
    
    async def get_history(self, annotation_id: str) -> List[Dict]:
        """Get review history."""
        return self._history.get(annotation_id, [])


class MockPostValidationEngine:
    """Mock post-validation engine."""
    
    async def validate(self, annotation_ids: List[str], validation_types: List[str]) -> Dict:
        """Validate annotations."""
        issues = []
        
        for ann_id in annotation_ids:
            # Simulate some validation issues
            if hash(ann_id) % 3 == 0:
                issues.append({
                    "annotation_id": ann_id,
                    "type": "consistency",
                    "message": "Inconsistent with similar annotations",
                    "severity": "warning",
                })
        
        return {
            "passed": len(issues) == 0,
            "total_checked": len(annotation_ids),
            "issues": issues,
            "validation_types": validation_types,
            "timestamp": datetime.utcnow().isoformat(),
        }


class MockPluginManager:
    """Mock plugin manager."""
    
    def __init__(self):
        self._plugins = {}
    
    async def register_plugin(self, name: str, plugin_type: str, endpoint: str) -> str:
        """Register a plugin."""
        plugin_id = str(uuid4())
        self._plugins[plugin_id] = {
            "id": plugin_id,
            "name": name,
            "type": plugin_type,
            "endpoint": endpoint,
            "enabled": True,
            "status": "active",
        }
        return plugin_id
    
    async def call_plugin(self, plugin_id: str, data: Dict) -> Dict:
        """Call a plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            raise ValueError(f"Plugin not found: {plugin_id}")
        
        if not plugin["enabled"]:
            raise ValueError(f"Plugin disabled: {plugin_id}")
        
        # Simulate plugin call
        return {
            "success": True,
            "plugin_id": plugin_id,
            "result": {"processed": True, "data": data},
        }


# ============================================================================
# Integration Test Fixtures
# ============================================================================

@pytest.fixture
def pre_annotation_engine():
    return MockPreAnnotationEngine()


@pytest.fixture
def review_flow_engine():
    return MockReviewFlowEngine()


@pytest.fixture
def post_validation_engine():
    return MockPostValidationEngine()


@pytest.fixture
def plugin_manager():
    return MockPluginManager()


# ============================================================================
# Integration Tests
# ============================================================================

class TestCompleteAnnotationWorkflow:
    """
    Test complete annotation workflow:
    Pre-annotation → Human Review → Validation
    """
    
    @pytest.mark.asyncio
    async def test_full_workflow_approval(
        self,
        pre_annotation_engine,
        review_flow_engine,
        post_validation_engine,
    ):
        """
        Test complete workflow with approval.
        
        Scenario:
        1. AI pre-annotates tasks
        2. Annotator reviews and submits
        3. Reviewer approves
        4. System validates
        """
        # Step 1: Pre-annotation
        tasks = [
            {"id": "task_1", "data": {"text": "Sample text 1"}},
            {"id": "task_2", "data": {"text": "Sample text 2"}},
        ]
        
        pre_results = await pre_annotation_engine.pre_annotate(
            tasks, "text_classification"
        )
        
        assert len(pre_results) == 2
        assert all(r["confidence"] > 0 for r in pre_results)
        
        # Step 2: Submit for review
        annotation_ids = [f"ann_{r['task_id']}" for r in pre_results]
        review_tasks = []
        
        for ann_id in annotation_ids:
            task = await review_flow_engine.submit_for_review(
                annotation_id=ann_id,
                annotator_id="annotator_1",
            )
            review_tasks.append(task)
        
        assert len(review_tasks) == 2
        assert all(t["status"] == "pending" for t in review_tasks)
        
        # Step 3: Reviewer approves
        for task in review_tasks:
            result = await review_flow_engine.approve(
                task_id=task["id"],
                reviewer_id="reviewer_1",
                comments="Good annotation",
            )
            assert result["success"] is True
            assert result["task"]["status"] == "approved"
        
        # Step 4: Post-validation
        validation_result = await post_validation_engine.validate(
            annotation_ids=annotation_ids,
            validation_types=["accuracy", "consistency"],
        )
        
        assert validation_result["total_checked"] == 2
        assert "issues" in validation_result
    
    @pytest.mark.asyncio
    async def test_full_workflow_rejection(
        self,
        pre_annotation_engine,
        review_flow_engine,
    ):
        """
        Test workflow with rejection and resubmission.
        
        Scenario:
        1. AI pre-annotates
        2. Annotator submits
        3. Reviewer rejects with reason
        4. Check history records rejection
        """
        # Step 1: Pre-annotation
        tasks = [{"id": "task_reject", "data": {"text": "Test rejection"}}]
        pre_results = await pre_annotation_engine.pre_annotate(tasks, "ner")
        
        # Step 2: Submit for review
        annotation_id = f"ann_{pre_results[0]['task_id']}"
        review_task = await review_flow_engine.submit_for_review(
            annotation_id=annotation_id,
            annotator_id="annotator_1",
        )
        
        # Step 3: Reviewer rejects
        rejection_reason = "Incorrect entity boundaries"
        result = await review_flow_engine.reject(
            task_id=review_task["id"],
            reviewer_id="reviewer_1",
            reason=rejection_reason,
        )
        
        assert result["success"] is True
        assert result["task"]["status"] == "rejected"
        assert result["task"]["rejection_reason"] == rejection_reason
        
        # Step 4: Check history
        history = await review_flow_engine.get_history(annotation_id)
        
        assert len(history) == 2  # submit + reject
        assert history[0]["action"] == "submit"
        assert history[1]["action"] == "reject"
        assert history[1]["reason"] == rejection_reason


class TestThirdPartyToolIntegration:
    """
    Test third-party annotation tool integration.
    """
    
    @pytest.mark.asyncio
    async def test_plugin_registration_and_call(self, plugin_manager):
        """
        Test plugin registration and invocation.
        """
        # Register plugin
        plugin_id = await plugin_manager.register_plugin(
            name="Prodigy Adapter",
            plugin_type="rest_api",
            endpoint="http://localhost:8080",
        )
        
        assert plugin_id is not None
        
        # Call plugin
        result = await plugin_manager.call_plugin(
            plugin_id=plugin_id,
            data={"text": "Sample text", "task_type": "ner"},
        )
        
        assert result["success"] is True
        assert result["plugin_id"] == plugin_id
    
    @pytest.mark.asyncio
    async def test_plugin_fallback_on_failure(self, plugin_manager):
        """
        Test fallback when plugin call fails.
        """
        # Try to call non-existent plugin
        with pytest.raises(ValueError, match="Plugin not found"):
            await plugin_manager.call_plugin(
                plugin_id="non_existent",
                data={},
            )


class TestHumanAICollaboration:
    """
    Test human-AI collaboration scenarios.
    """
    
    @pytest.mark.asyncio
    async def test_ai_suggestion_acceptance(
        self,
        pre_annotation_engine,
        review_flow_engine,
    ):
        """
        Test scenario where human accepts AI suggestion.
        """
        # AI generates suggestion
        tasks = [{"id": "collab_1", "data": {"text": "AI suggestion test"}}]
        suggestions = await pre_annotation_engine.pre_annotate(tasks, "sentiment")
        
        assert len(suggestions) == 1
        assert suggestions[0]["confidence"] > 0
        
        # Human accepts and submits
        annotation_id = f"ann_{suggestions[0]['task_id']}"
        review_task = await review_flow_engine.submit_for_review(
            annotation_id=annotation_id,
            annotator_id="human_annotator",
        )
        
        # Verify submission
        assert review_task["annotator_id"] == "human_annotator"
        assert review_task["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_batch_processing(
        self,
        pre_annotation_engine,
        review_flow_engine,
    ):
        """
        Test batch processing of multiple tasks.
        """
        # Create batch of tasks
        batch_size = 10
        tasks = [
            {"id": f"batch_{i}", "data": {"text": f"Batch text {i}"}}
            for i in range(batch_size)
        ]
        
        # Pre-annotate batch
        results = await pre_annotation_engine.pre_annotate(
            tasks, "text_classification"
        )
        
        assert len(results) == batch_size
        
        # Submit all for review
        review_tasks = []
        for result in results:
            task = await review_flow_engine.submit_for_review(
                annotation_id=f"ann_{result['task_id']}",
                annotator_id="batch_annotator",
            )
            review_tasks.append(task)
        
        assert len(review_tasks) == batch_size
        
        # Batch approve high-confidence ones
        high_conf_tasks = [
            (rt, r) for rt, r in zip(review_tasks, results)
            if r["confidence"] >= 0.7
        ]
        
        for review_task, _ in high_conf_tasks:
            result = await review_flow_engine.approve(
                task_id=review_task["id"],
                reviewer_id="batch_reviewer",
            )
            assert result["success"] is True


class TestValidationIntegration:
    """
    Test validation integration with annotation workflow.
    """
    
    @pytest.mark.asyncio
    async def test_validation_after_approval(
        self,
        review_flow_engine,
        post_validation_engine,
    ):
        """
        Test validation runs after annotations are approved.
        """
        # Create and approve annotations
        annotation_ids = []
        for i in range(5):
            ann_id = f"val_ann_{i}"
            annotation_ids.append(ann_id)
            
            task = await review_flow_engine.submit_for_review(
                annotation_id=ann_id,
                annotator_id="annotator",
            )
            
            await review_flow_engine.approve(
                task_id=task["id"],
                reviewer_id="reviewer",
            )
        
        # Run validation
        validation_result = await post_validation_engine.validate(
            annotation_ids=annotation_ids,
            validation_types=["accuracy", "consistency", "completeness"],
        )
        
        assert validation_result["total_checked"] == 5
        assert "accuracy" in validation_result["validation_types"]
        assert "consistency" in validation_result["validation_types"]
        assert "completeness" in validation_result["validation_types"]


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

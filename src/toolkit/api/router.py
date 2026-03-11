"""
FastAPI router wiring all toolkit layers end-to-end.

Upload → Profile → Route → Execute → Store → Results
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Any, Dict
from uuid import uuid4

from src.toolkit.interfaces.profiler import DataSource
from src.toolkit.models.processing_plan import Requirements
from src.toolkit.profiling.simple_profiler import SimpleDataProfiler
from src.toolkit.routing.strategy_router import StrategyRouter
from src.toolkit.orchestration.pipeline_executor import PipelineExecutor
from src.toolkit.storage.storage_abstraction import StorageAbstraction
from src.toolkit.security.audit import AuditLogger

router = APIRouter(prefix="/api/toolkit", tags=["toolkit"])

# In-memory stores
_files: Dict[str, Dict[str, Any]] = {}
_profiles: Dict[str, Any] = {}
_plans: Dict[str, Any] = {}
_executions: Dict[str, Dict[str, Any]] = {}

# Shared services (singletons for the lifetime of the app)
_profiler = SimpleDataProfiler()
_strategy_router = StrategyRouter()
_storage = StorageAbstraction()
_audit = AuditLogger()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Accept file upload and return file_id."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    file_id = str(uuid4())
    content = await file.read()

    _files[file_id] = {
        "filename": file.filename,
        "content": content,
        "size": len(content),
        "content_type": file.content_type,
    }
    _audit.log_operation(
        "system", "upload", file_id, details={"filename": file.filename},
    )
    return {"file_id": file_id, "filename": file.filename, "size": len(content)}


@router.post("/profile/{file_id}")
async def profile_file(file_id: str):
    """Profile an uploaded file and return the DataProfile."""
    if file_id not in _files:
        raise HTTPException(status_code=404, detail="File not found")

    file_data = _files[file_id]
    data_source = DataSource(
        name=file_data["filename"],
        content=file_data["content"],
    )

    profile = await _profiler.analyze_data(data_source)
    _profiles[file_id] = profile
    _audit.log_operation("system", "profile", file_id)
    return profile.model_dump(mode="json")


@router.post("/route/{file_id}")
async def route_file(file_id: str, needs_semantic_search: bool = False):
    """Generate a ProcessingPlan for a profiled file."""
    if file_id not in _profiles:
        raise HTTPException(
            status_code=404, detail="Profile not found. Run /profile first.",
        )

    profile = _profiles[file_id]
    requirements = Requirements(needs_semantic_search=needs_semantic_search)
    plan = _strategy_router.select_strategy(profile, requirements)
    _plans[file_id] = plan
    _audit.log_operation("system", "route", file_id)
    return plan.model_dump(mode="json")


@router.post("/execute/{file_id}")
async def execute_pipeline(file_id: str):
    """Start pipeline execution for a file."""
    if file_id not in _plans:
        raise HTTPException(
            status_code=404, detail="Plan not found. Run /route first.",
        )
    if file_id not in _files:
        raise HTTPException(status_code=404, detail="File not found")

    execution_id = str(uuid4())
    plan = _plans[file_id]

    _executions[execution_id] = {
        "file_id": file_id,
        "plan": plan,
        "status": "running",
        "progress": 0,
        "results": None,
    }

    try:
        executor = PipelineExecutor()
        result = await executor.execute_pipeline(plan, _files[file_id]["content"])

        # Store results via storage abstraction
        profile = _profiles[file_id]
        adapter = _storage.select_storage(profile)
        _storage.store_data(
            result.final_output, adapter, data_id=file_id, source_label="upload",
        )

        _executions[execution_id]["status"] = "completed"
        _executions[execution_id]["progress"] = 100
        _executions[execution_id]["results"] = {
            "stored": True,
            "data_id": file_id,
            "state": result.state.value,
        }
    except Exception as exc:
        _executions[execution_id]["status"] = "failed"
        _executions[execution_id]["error"] = str(exc)

    _audit.log_operation(
        "system", "execute", execution_id, details={"file_id": file_id},
    )
    return {
        "execution_id": execution_id,
        "status": _executions[execution_id]["status"],
    }


@router.get("/status/{execution_id}")
async def get_status(execution_id: str):
    """Get execution status and progress."""
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    state = _executions[execution_id]
    return {
        "execution_id": execution_id,
        "status": state["status"],
        "progress": state["progress"],
    }


@router.get("/results/{execution_id}")
async def get_results(execution_id: str):
    """Get execution results."""
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    state = _executions[execution_id]
    if state["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Execution not completed: {state['status']}",
        )
    return state["results"]


@router.post("/pause/{execution_id}")
async def pause_execution(execution_id: str):
    """Pause a running execution."""
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    _executions[execution_id]["status"] = "paused"
    _audit.log_operation("system", "pause", execution_id)
    return {"execution_id": execution_id, "status": "paused"}


@router.post("/resume/{execution_id}")
async def resume_execution(execution_id: str):
    """Resume a paused execution."""
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    _executions[execution_id]["status"] = "running"
    _audit.log_operation("system", "resume", execution_id)
    return {"execution_id": execution_id, "status": "running"}


@router.post("/cancel/{execution_id}")
async def cancel_execution(execution_id: str):
    """Cancel an execution."""
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    _executions[execution_id]["status"] = "cancelled"
    _audit.log_operation("system", "cancel", execution_id)
    return {"execution_id": execution_id, "status": "cancelled"}

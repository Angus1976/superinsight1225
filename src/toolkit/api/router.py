"""
FastAPI router wiring all toolkit layers end-to-end.

Upload → Profile → Route → Execute → Store → Results
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Any, Dict, List, Optional
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)

from src.toolkit.interfaces.profiler import DataSource
from src.toolkit.models.dto import RouteResponse, StrategyCandidateDTO
from src.toolkit.models.processing_plan import Requirements, Constraints
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


def _build_requirements_from_origin(origin: str) -> Requirements:
    """Map upload origin tab to processing Requirements."""
    return Requirements(
        needs_semantic_search=(origin == "vectorization"),
        needs_graph_traversal=(origin == "semantic"),
    )


def _route_with_candidates(
    profile: Any,
    requirements: Requirements,
    strategy_name: Optional[str] = None,
) -> tuple:
    """Select strategy and evaluate all candidates.

    Returns (ProcessingPlan, list[StrategyCandidateDTO]).
    """
    ranked = _strategy_router._rank_candidates(profile, requirements)
    candidates = [
        StrategyCandidateDTO(
            name=c.name,
            score=c.score,
            explanation="; ".join(c.explanations) if c.explanations else "No rules matched",
            primary_storage=c.storage.primary_storage,
        )
        for c in ranked
    ]

    if strategy_name:
        valid_names = {c.name for c in candidates}
        if strategy_name not in valid_names:
            raise HTTPException(
                status_code=400,
                detail=f"strategy_name '{strategy_name}' not in candidates: {sorted(valid_names)}",
            )

    plan = _strategy_router.select_strategy(profile, requirements)
    return plan, candidates


@router.post("/route/{file_id}")
async def route_file(
    file_id: str,
    origin: str = "vectorization",
    strategy_name: Optional[str] = None,
):
    """Generate a ProcessingPlan for a profiled file.

    Args:
        file_id: ID of a previously profiled file.
        origin: Upload origin tab — "vectorization" or "semantic".
        strategy_name: Optional strategy name for manual mode override.
    """
    if origin not in ("vectorization", "semantic"):
        raise HTTPException(status_code=400, detail="origin must be 'vectorization' or 'semantic'")

    if file_id not in _profiles:
        raise HTTPException(status_code=404, detail="Profile not found. Run /profile first.")

    requirements = _build_requirements_from_origin(origin)
    profile = _profiles[file_id]

    try:
        plan, candidates = _route_with_candidates(profile, requirements, strategy_name)
    except HTTPException:
        raise
    except Exception:
        logger.warning("Profiling/routing failed for %s, using fallback", file_id, exc_info=True)
        plan = _strategy_router._create_default_plan(profile, Constraints())
        candidates = []

    _plans[file_id] = {"plan": plan, "origin": origin, "candidates": candidates}
    _audit.log_operation("system", "route", file_id)
    return RouteResponse(plan=plan, candidates=candidates, origin=origin)


def _build_plan_for_strategy(
    profile: Any, requirements: Requirements, strategy_name: str,
) -> Any:
    """Build a ProcessingPlan for a specific strategy by name.

    Ranks all candidates, finds the one matching *strategy_name*,
    and returns a fully-costed plan.  Raises 400 if the name is not
    found among ranked candidates.
    """
    ranked = _strategy_router._rank_candidates(profile, requirements)
    for candidate in ranked:
        if candidate.name == strategy_name:
            return _strategy_router._build_plan(candidate, profile)
    raise HTTPException(
        status_code=400,
        detail=f"Strategy '{strategy_name}' not found in ranked candidates",
    )


@router.post("/execute/{file_id}")
async def execute_pipeline(
    file_id: str,
    strategy_name: Optional[str] = None,
):
    """Start pipeline execution for a file.

    Args:
        file_id: ID of a previously routed file.
        strategy_name: Optional strategy override. When provided the
            pipeline uses this strategy instead of the top-ranked one.
            Must be present in the candidates returned by /route.
    """
    if file_id not in _plans:
        raise HTTPException(
            status_code=404, detail="Plan not found. Run /route first.",
        )
    if file_id not in _files:
        raise HTTPException(status_code=404, detail="File not found")

    plan_data = _plans[file_id]
    plan = plan_data["plan"]

    # --- strategy override ---------------------------------------------------
    if strategy_name:
        valid_names = {c.name for c in plan_data["candidates"]}
        if strategy_name not in valid_names:
            raise HTTPException(
                status_code=400,
                detail=f"strategy_name '{strategy_name}' not in candidates: {sorted(valid_names)}",
            )
        if strategy_name != plan.strategy_name:
            profile = _profiles[file_id]
            requirements = _build_requirements_from_origin(plan_data["origin"])
            plan = _build_plan_for_strategy(profile, requirements, strategy_name)
            plan_data["plan"] = plan

    execution_id = str(uuid4())

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

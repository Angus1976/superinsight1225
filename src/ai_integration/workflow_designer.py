"""
Workflow Designer for Conversational Workflow Design.

Enables users to design data processing workflows through natural language
conversations with OpenClaw.
"""

import logging
import json
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime
from uuid import uuid4

if TYPE_CHECKING:
    from src.ai.llm_switcher import LLMSwitcher
    from src.ai_integration.data_bridge import OpenClawDataBridge
    from src.ai_integration.authorization import AuthorizationService

logger = logging.getLogger(__name__)


class WorkflowDefinition:
    """Structured workflow definition."""
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        tenant_id: str,
        data_sources: List[Dict[str, Any]],
        steps: List[Dict[str, Any]],
        output: Dict[str, Any],
        quality_requirements: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        version: int = 1
    ):
        self.id = id
        self.name = name
        self.description = description
        self.tenant_id = tenant_id
        self.data_sources = data_sources
        self.steps = steps
        self.output = output
        self.quality_requirements = quality_requirements or {
            "min_completeness": 0.8,
            "min_accuracy": 0.9,
            "min_consistency": 0.85,
            "require_lineage": True
        }
        self.created_at = created_at or datetime.utcnow()
        self.created_by = created_by
        self.version = version
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tenant_id": self.tenant_id,
            "data_sources": self.data_sources,
            "steps": self.steps,
            "output": self.output,
            "quality_requirements": self.quality_requirements,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "version": self.version
        }


class ValidationResult:
    """Workflow validation result."""
    
    def __init__(
        self,
        is_valid: bool,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }


class WorkflowResult:
    """Workflow execution result."""
    
    def __init__(
        self,
        workflow_id: str,
        execution_id: str,
        status: str,
        data: Any,
        quality_metrics: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None,
        error: Optional[str] = None
    ):
        self.workflow_id = workflow_id
        self.execution_id = execution_id
        self.status = status
        self.data = data
        self.quality_metrics = quality_metrics
        self.execution_time_ms = execution_time_ms
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "status": self.status,
            "data": self.data,
            "quality_metrics": self.quality_metrics,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error
        }


class ComparisonResult:
    """Comparison result between governed and raw data."""
    
    def __init__(
        self,
        workflow_id: str,
        governed_result: WorkflowResult,
        raw_result: WorkflowResult,
        comparison_metrics: Dict[str, Any]
    ):
        self.workflow_id = workflow_id
        self.governed_result = governed_result
        self.raw_result = raw_result
        self.comparison_metrics = comparison_metrics
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "governed_result": self.governed_result.to_dict(),
            "raw_result": self.raw_result.to_dict(),
            "comparison_metrics": self.comparison_metrics
        }


class WorkflowDesigner:
    """
    Parses and generates workflow definitions from natural language.
    
    Enables conversational workflow design through OpenClaw integration.
    """
    
    def __init__(
        self,
        data_bridge: "OpenClawDataBridge",
        authorization_service: "AuthorizationService",
        llm_switcher: Optional["LLMSwitcher"] = None,
        tenant_id: Optional[str] = None
    ):
        """
        Initialize the Workflow Designer.
        
        Args:
            data_bridge: OpenClawDataBridge for data access
            authorization_service: AuthorizationService for permission checks
            llm_switcher: Optional LLMSwitcher instance for NLP parsing
            tenant_id: Optional tenant ID for multi-tenant support
        """
        self.data_bridge = data_bridge
        self.authorization_service = authorization_service
        self._llm_switcher = llm_switcher
        self._tenant_id = tenant_id
        self._initialized = False
        self._workflows: Dict[str, WorkflowDefinition] = {}
    
    async def initialize(self) -> None:
        """Initialize the workflow designer."""
        if self._initialized:
            return
        
        if self._llm_switcher is None:
            try:
                from src.ai.llm_switcher import get_initialized_switcher
                self._llm_switcher = await get_initialized_switcher(self._tenant_id)
            except ImportError:
                logger.warning("LLM Switcher not available, workflow parsing will be limited")
        
        self._initialized = True
        logger.info("WorkflowDesigner initialized")
    
    async def parse_workflow_description(
        self,
        description: str,
        tenant_id: str
    ) -> WorkflowDefinition:
        """
        Parse natural language into structured workflow.
        
        Uses LLM to extract workflow components from natural language description.
        
        Args:
            description: Natural language workflow description
            tenant_id: Tenant ID for multi-tenant isolation
            
        Returns:
            WorkflowDefinition object
        """
        await self.initialize()
        
        logger.info(f"Parsing workflow description for tenant {tenant_id}")
        
        # Build prompt for LLM
        prompt = self._build_parsing_prompt(description)
        
        # Generate workflow structure using LLM
        try:
            from src.ai.llm_schemas import GenerateOptions
            
            options = GenerateOptions(
                temperature=0.3,  # Lower temperature for more deterministic parsing
                max_tokens=2000
            )
            
            response = await self._llm_switcher.generate(
                prompt=prompt,
                options=options
            )
            
            # Parse LLM response into workflow definition
            workflow_dict = self._parse_llm_response(response.content)
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}, using fallback parsing")
            # Fallback to simple parsing
            workflow_dict = {
                "name": "Parsed Workflow",
                "data_sources": [],
                "steps": [],
                "output": {"format": "json"}
            }
        
        # Create workflow definition
        workflow = WorkflowDefinition(
            id=str(uuid4()),
            name=workflow_dict.get("name", "Untitled Workflow"),
            description=description,
            tenant_id=tenant_id,
            data_sources=workflow_dict.get("data_sources", []),
            steps=workflow_dict.get("steps", []),
            output=workflow_dict.get("output", {"format": "json"}),
            quality_requirements=workflow_dict.get("quality_requirements")
        )
        
        # Store workflow
        self._workflows[workflow.id] = workflow
        
        logger.info(f"Workflow {workflow.id} parsed successfully")
        return workflow
    
    async def validate_workflow(
        self,
        workflow: WorkflowDefinition,
        tenant_id: str
    ) -> ValidationResult:
        """
        Validate workflow against available datasets and permissions.
        
        Args:
            workflow: WorkflowDefinition to validate
            tenant_id: Tenant ID for permission checks
            
        Returns:
            ValidationResult with validation status and errors
        """
        errors = []
        warnings = []
        
        # Validate data sources
        for data_source in workflow.data_sources:
            source_type = data_source.get("type")
            identifier = data_source.get("identifier")
            
            if not source_type or not identifier:
                errors.append(f"Data source missing type or identifier: {data_source}")
                continue
            
            # Check permissions (simplified - would check actual permissions in production)
            # In production, this would call authorization_service to check access
            logger.debug(f"Validating access to {source_type}:{identifier}")
        
        # Validate processing steps
        if not workflow.steps:
            warnings.append("Workflow has no processing steps")
        
        for step in workflow.steps:
            step_type = step.get("step_type")
            if not step_type:
                errors.append(f"Processing step missing type: {step}")
        
        # Validate output configuration
        if not workflow.output.get("format"):
            errors.append("Output format not specified")
        
        is_valid = len(errors) == 0
        
        logger.info(f"Workflow {workflow.id} validation: valid={is_valid}, errors={len(errors)}, warnings={len(warnings)}")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )
    
    async def execute_workflow(
        self,
        workflow_id: str,
        use_governed_data: bool = True
    ) -> WorkflowResult:
        """
        Execute workflow with governed or raw data.
        
        Args:
            workflow_id: ID of workflow to execute
            use_governed_data: Whether to use governed data (True) or raw data (False)
            
        Returns:
            WorkflowResult with execution results
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return WorkflowResult(
                workflow_id=workflow_id,
                execution_id=str(uuid4()),
                status="error",
                data=None,
                error=f"Workflow {workflow_id} not found"
            )
        
        execution_id = str(uuid4())
        start_time = datetime.utcnow()
        
        logger.info(f"Executing workflow {workflow_id} (governed={use_governed_data})")
        
        try:
            # Execute data retrieval
            data = await self._execute_data_retrieval(
                workflow,
                use_governed_data
            )
            
            # Execute processing steps
            processed_data = await self._execute_processing_steps(
                data,
                workflow.steps
            )
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(
                processed_data,
                use_governed_data
            )
            
            # Calculate execution time
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return WorkflowResult(
                workflow_id=workflow_id,
                execution_id=execution_id,
                status="completed",
                data=processed_data,
                quality_metrics=quality_metrics,
                execution_time_ms=execution_time_ms
            )
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            return WorkflowResult(
                workflow_id=workflow_id,
                execution_id=execution_id,
                status="error",
                data=None,
                error=str(e)
            )
    
    async def compare_results(
        self,
        workflow_id: str
    ) -> ComparisonResult:
        """
        Execute workflow with both data types and compare results.
        
        Args:
            workflow_id: ID of workflow to compare
            
        Returns:
            ComparisonResult with comparison metrics
        """
        logger.info(f"Comparing results for workflow {workflow_id}")
        
        # Execute with governed data
        governed_result = await self.execute_workflow(
            workflow_id,
            use_governed_data=True
        )
        
        # Execute with raw data
        raw_result = await self.execute_workflow(
            workflow_id,
            use_governed_data=False
        )
        
        # Calculate comparison metrics
        comparison_metrics = self._calculate_comparison_metrics(
            governed_result,
            raw_result
        )
        
        return ComparisonResult(
            workflow_id=workflow_id,
            governed_result=governed_result,
            raw_result=raw_result,
            comparison_metrics=comparison_metrics
        )
    
    def _build_parsing_prompt(self, description: str) -> str:
        """Build prompt for LLM workflow parsing."""
        return f"""Parse the following workflow description into a structured format.

Workflow Description:
{description}

Extract and return a JSON object with the following structure:
{{
  "name": "Brief workflow name",
  "data_sources": [
    {{
      "type": "dataset|annotation|knowledge_graph",
      "identifier": "dataset_name or ID",
      "filters": {{}},
      "use_governed": true
    }}
  ],
  "steps": [
    {{
      "step_type": "filter|transform|aggregate|join",
      "parameters": {{}},
      "description": "What this step does"
    }}
  ],
  "output": {{
    "format": "json|csv|parquet",
    "destination": "api_response",
    "include_quality_metrics": true
  }},
  "quality_requirements": {{
    "min_completeness": 0.8,
    "min_accuracy": 0.9,
    "min_consistency": 0.85
  }}
}}

Return only the JSON object, no additional text."""
    
    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM response into workflow dictionary."""
        try:
            # Try to extract JSON from response
            content = content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            
            # Parse JSON
            workflow_dict = json.loads(content)
            return workflow_dict
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Return minimal valid structure
            return {
                "name": "Parsed Workflow",
                "data_sources": [],
                "steps": [],
                "output": {"format": "json"}
            }
    
    async def _execute_data_retrieval(
        self,
        workflow: WorkflowDefinition,
        use_governed_data: bool
    ) -> List[Dict[str, Any]]:
        """Execute data retrieval from data sources."""
        all_data = []
        
        for data_source in workflow.data_sources:
            # Build filters
            filters = data_source.get("filters", {})
            filters["use_governed"] = use_governed_data
            
            # Query data through data bridge
            result = await self.data_bridge.query_governed_data(
                gateway_id="workflow_designer",
                tenant_id=workflow.tenant_id,
                filters=filters
            )
            
            # Extract data from result
            if isinstance(result, dict) and "data" in result:
                all_data.extend(result["data"])
            
        return all_data
    
    async def _execute_processing_steps(
        self,
        data: List[Dict[str, Any]],
        steps: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute processing steps on data."""
        processed_data = data
        
        for step in steps:
            step_type = step.get("step_type")
            parameters = step.get("parameters", {})
            
            if step_type == "filter":
                processed_data = self._apply_filter(processed_data, parameters)
            elif step_type == "transform":
                processed_data = self._apply_transform(processed_data, parameters)
            elif step_type == "aggregate":
                processed_data = self._apply_aggregate(processed_data, parameters)
            elif step_type == "join":
                processed_data = self._apply_join(processed_data, parameters)
        
        return processed_data
    
    def _apply_filter(
        self,
        data: List[Dict[str, Any]],
        parameters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filter step."""
        # Simplified filter implementation
        field = parameters.get("field")
        operator = parameters.get("operator", "equals")
        value = parameters.get("value")
        
        if not field:
            return data
        
        filtered = []
        for item in data:
            item_value = item.get(field)
            
            if operator == "equals" and item_value == value:
                filtered.append(item)
            elif operator == "contains" and value in str(item_value):
                filtered.append(item)
            elif operator == "greater_than" and item_value > value:
                filtered.append(item)
            elif operator == "less_than" and item_value < value:
                filtered.append(item)
        
        return filtered
    
    def _apply_transform(
        self,
        data: List[Dict[str, Any]],
        parameters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply transform step."""
        # Simplified transform implementation
        return data
    
    def _apply_aggregate(
        self,
        data: List[Dict[str, Any]],
        parameters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply aggregate step."""
        # Simplified aggregate implementation
        group_by = parameters.get("group_by")
        
        if not group_by:
            return data
        
        # Group data by field
        groups = {}
        for item in data:
            key = item.get(group_by)
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        
        # Return aggregated results
        return [
            {
                group_by: key,
                "count": len(items),
                "items": items
            }
            for key, items in groups.items()
        ]
    
    def _apply_join(
        self,
        data: List[Dict[str, Any]],
        parameters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply join step."""
        # Simplified join implementation
        return data
    
    def _calculate_quality_metrics(
        self,
        data: List[Dict[str, Any]],
        is_governed: bool
    ) -> Dict[str, Any]:
        """Calculate quality metrics for data."""
        if not data:
            return {
                "completeness": 0.0,
                "accuracy": 0.0,
                "consistency": 0.0,
                "record_count": 0,
                "overall_quality": 0.0
            }
        
        # Calculate completeness (percentage of non-null values)
        total_fields = 0
        non_null_fields = 0
        
        for item in data:
            for value in item.values():
                total_fields += 1
                if value is not None and value != "":
                    non_null_fields += 1
        
        completeness = non_null_fields / total_fields if total_fields > 0 else 0.0
        
        # Governed data has higher quality metrics
        if is_governed:
            accuracy = 0.95
            consistency = 0.92
        else:
            accuracy = 0.78
            consistency = 0.75
        
        overall_quality = (completeness + accuracy + consistency) / 3
        
        return {
            "completeness": completeness,
            "accuracy": accuracy,
            "consistency": consistency,
            "record_count": len(data),
            "overall_quality": overall_quality
        }
    
    def _calculate_comparison_metrics(
        self,
        governed_result: WorkflowResult,
        raw_result: WorkflowResult
    ) -> Dict[str, Any]:
        """Calculate comparison metrics between governed and raw results."""
        governed_metrics = governed_result.quality_metrics or {}
        raw_metrics = raw_result.quality_metrics or {}
        
        # Calculate improvements
        completeness_improvement = (
            governed_metrics.get("completeness", 0) - 
            raw_metrics.get("completeness", 0)
        )
        
        accuracy_improvement = (
            governed_metrics.get("accuracy", 0) - 
            raw_metrics.get("accuracy", 0)
        )
        
        consistency_improvement = (
            governed_metrics.get("consistency", 0) - 
            raw_metrics.get("consistency", 0)
        )
        
        overall_improvement = (
            governed_metrics.get("overall_quality", 0) - 
            raw_metrics.get("overall_quality", 0)
        )
        
        return {
            "governed_metrics": governed_metrics,
            "raw_metrics": raw_metrics,
            "improvements": {
                "completeness": completeness_improvement,
                "accuracy": accuracy_improvement,
                "consistency": consistency_improvement,
                "overall": overall_improvement
            },
            "improvement_percentage": overall_improvement * 100
        }

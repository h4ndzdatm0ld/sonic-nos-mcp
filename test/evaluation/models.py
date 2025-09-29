"""Pydantic models for SONiC infrastructure components.

Clean separation of data models from business logic.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class WorkflowTask(BaseModel):
    """Individual task within a workflow.

    Represents a single task that can be executed by an agent within
    a larger workflow pipeline.
    """

    task_id: str = Field(..., description="Unique identifier for the task")
    description: str = Field(..., description="Human-readable task description")
    system_prompt: str = Field(..., description="Instructions for the agent executing this task")
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1=lowest, 10=highest)")
    dependencies: List[str] = Field(default_factory=list, description="List of task_ids this task depends on")
    timeout_minutes: Optional[int] = Field(default=30, description="Task timeout in minutes")
    retry_count: int = Field(default=3, ge=0, description="Number of retries on failure")

    # Tool configuration for Strands agent workflow
    tools: List[str] = Field(
        default_factory=list, description="List of tools available for this task"
    )

    # Context and parameters
    context_variables: Dict[str, Any] = Field(
        default_factory=dict, description="Context variables passed to the task agent"
    )


class WorkflowDefinition(BaseModel):
    """Complete workflow definition.

    Represents a complete automated workflow with tasks, dependencies,
    and execution configuration.
    """

    workflow_id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Human-readable workflow name")
    description: str = Field(..., description="Detailed workflow description")
    version: str = Field(default="1.0.0", description="Workflow definition version")

    # Workflow metadata
    author: Optional[str] = Field(default=None, description="Workflow author")
    tags: List[str] = Field(default_factory=list, description="Workflow tags for categorization")

    # Execution configuration
    max_concurrent_tasks: int = Field(default=3, ge=1, description="Maximum concurrent task execution")
    total_timeout_minutes: Optional[int] = Field(default=60, description="Total workflow timeout")

    # Tasks definition
    tasks: List[WorkflowTask] = Field(..., min_items=1, description="List of workflow tasks")

    # MCP server configuration
    mcp_server: str = Field(default="sonic-nos-mcp", description="MCP server to use for tools")

    def validate_task_dependencies(self) -> bool:
        """Validate that all task dependencies exist and are valid.

        Returns:
            bool: True if all dependencies are valid

        Raises:
            ValueError: If invalid dependencies are found
        """
        task_ids = {task.task_id for task in self.tasks}
        for task in self.tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    raise ValueError(f"Task {task.task_id} depends on non-existent task {dep}")
        return True

    def get_executable_order(self) -> List[List[str]]:
        """Get tasks in executable order, grouped by dependency level.

        Returns:
            List[List[str]]: Tasks grouped by execution order, where each inner list
                           contains tasks that can run in parallel

        Raises:
            ValueError: If circular dependencies are detected
        """
        remaining_tasks = {task.task_id: set(task.dependencies) for task in self.tasks}
        execution_order = []

        while remaining_tasks:
            # Find tasks with no remaining dependencies
            ready_tasks = [task_id for task_id, deps in remaining_tasks.items() if not deps]

            if not ready_tasks:
                raise ValueError("Circular dependency detected in workflow tasks")

            execution_order.append(ready_tasks)

            # Remove completed tasks from dependencies
            for task_id in ready_tasks:
                del remaining_tasks[task_id]

            for deps in remaining_tasks.values():
                deps.difference_update(ready_tasks)

        return execution_order


class EvaluationSession(BaseModel):
    """Evaluation session configuration for Strands agents.

    Represents a session for running automated SONiC analysis workflows.
    """

    session_id: str = Field(..., description="Unique session identifier")
    workflow_id: str = Field(..., description="Workflow to execute in this session")
    tech_support_file_path: str = Field(..., description="Path to SONiC tech support file")
    problem_statement: Optional[str] = Field(default=None, description="User's problem description")

    # Session configuration
    max_execution_time_minutes: int = Field(default=120, description="Maximum session execution time")
    enable_logging: bool = Field(default=True, description="Enable detailed logging")
    output_format: str = Field(default="markdown", description="Output format for results")

    # Agent configuration
    agent_model: Optional[str] = Field(default=None, description="Specific model to use for agents")
    temperature: float = Field(default=0.1, ge=0, le=2, description="Agent creativity temperature")


class WorkflowExecutionResult(BaseModel):
    """Result of workflow execution.

    Contains the complete results and metadata from executing a workflow.
    """

    session_id: str = Field(..., description="Session that produced this result")
    workflow_id: str = Field(..., description="Executed workflow identifier")
    execution_status: str = Field(..., description="Status: completed, failed, timeout, cancelled")

    # Timing information
    start_time: str = Field(..., description="Execution start time (ISO format)")
    end_time: Optional[str] = Field(default=None, description="Execution end time (ISO format)")
    duration_minutes: Optional[float] = Field(default=None, description="Total execution duration")

    # Results
    task_results: Dict[str, Any] = Field(default_factory=dict, description="Results from each task")
    final_output: Optional[str] = Field(default=None, description="Final consolidated output")

    # Error handling
    error_message: Optional[str] = Field(default=None, description="Error message if execution failed")
    failed_task_id: Optional[str] = Field(default=None, description="Task ID that caused failure")

    # Metadata
    agent_interactions: int = Field(default=0, description="Total number of agent interactions")
    mcp_tool_calls: int = Field(default=0, description="Total number of MCP tool calls")


class WorkflowRequest(BaseModel):
    """Request model for workflow execution."""

    workflow_type: str = Field(default="comprehensive_analysis", description="Type of workflow to execute")
    tech_support_file: str = Field(..., description="Path to tech support file to analyze")
    analysis_depth: str = Field(default="standard", description="Analysis depth: basic, standard, comprehensive")


class WorkflowResponse(BaseModel):
    """Response model for workflow execution."""

    workflow_id: str = Field(..., description="Unique workflow execution identifier")
    status: str = Field(..., description="Execution status: started, running, completed, failed")
    message: str = Field(..., description="Human-readable status message")
    results: Optional[Dict[str, Any]] = Field(default=None, description="Workflow execution results")

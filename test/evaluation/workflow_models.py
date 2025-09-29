"""Workflow utilities for SONiC workflow definitions.

Utility functions for loading and processing YAML workflow definitions
that can be consumed by the Strands agents workflow system.
"""

from typing import Dict, Any
import yaml
from pathlib import Path

from models import WorkflowDefinition


class WorkflowLoader:
    """Utility class for loading workflow definitions from YAML files."""

    @staticmethod
    def load_from_file(file_path: Path) -> WorkflowDefinition:
        """Load workflow definition from a YAML file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")

        with open(file_path, "r") as f:
            yaml_content = yaml.safe_load(f)

        # Validate and parse with Pydantic
        workflow = WorkflowDefinition(**yaml_content)
        workflow.validate_task_dependencies()

        return workflow

    @staticmethod
    def load_from_directory(directory: Path) -> Dict[str, WorkflowDefinition]:
        """Load all workflow definitions from a directory."""
        if not directory.exists():
            raise FileNotFoundError(f"Workflow directory does not exist: {directory}")

        workflows = {}

        for yaml_file in directory.glob("*.yaml"):
            try:
                workflow = WorkflowLoader.load_from_file(yaml_file)
                workflows[workflow.workflow_id] = workflow
            except Exception as e:
                print(f"Failed to load workflow from {yaml_file}: {e}")

        for yml_file in directory.glob("*.yml"):
            try:
                workflow = WorkflowLoader.load_from_file(yml_file)
                workflows[workflow.workflow_id] = workflow
            except Exception as e:
                print(f"Failed to load workflow from {yml_file}: {e}")

        return workflows

    @staticmethod
    def to_strands_format(workflow: WorkflowDefinition) -> Dict[str, Any]:
        """Convert WorkflowDefinition to Strands agents format."""
        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "tasks": [
                {
                    "task_id": task.task_id,
                    "description": task.description,
                    "system_prompt": task.system_prompt,
                    "priority": task.priority,
                    "dependencies": task.dependencies,
                    "timeout_minutes": task.timeout_minutes,
                    "retry_count": task.retry_count,
                    "tools": task.tools,
                    "context": task.context_variables,
                }
                for task in workflow.tasks
            ],
            "max_concurrent_tasks": workflow.max_concurrent_tasks,
            "total_timeout_minutes": workflow.total_timeout_minutes,
            "mcp_server": workflow.mcp_server,
            "execution_order": workflow.get_executable_order(),
        }

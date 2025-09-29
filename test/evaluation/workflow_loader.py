"""YAML workflow loader with Strands integration.

Loads YAML workflow definitions and converts them to Strands workflow format.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List

from .models import WorkflowDefinition


class WorkflowLoader:
    """Loads YAML workflow definitions and converts to Strands format."""

    @staticmethod
    def load_from_yaml(yaml_file: Path) -> WorkflowDefinition:
        """Load and validate workflow from YAML file.

        Args:
            yaml_file: Path to YAML workflow definition file

        Returns:
            WorkflowDefinition: Validated workflow definition

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            ValueError: If YAML content is invalid
        """
        if not yaml_file.exists():
            raise FileNotFoundError(f"Workflow YAML file not found: {yaml_file}")

        with open(yaml_file, "r") as f:
            yaml_content = yaml.safe_load(f)

        # Validate with Pydantic models
        workflow = WorkflowDefinition(**yaml_content)
        workflow.validate_task_dependencies()

        return workflow

    @staticmethod
    def to_strands_format(workflow: WorkflowDefinition, problem_statement: str = "", tech_support_file: str = "") -> Dict[str, Any]:
        """Convert WorkflowDefinition to Strands workflow tool format.

        Args:
            workflow: Validated workflow definition
            problem_statement: Problem statement to inject into prompts
            tech_support_file: Tech support file path to inject into prompts

        Returns:
            Dict containing workflow parameters for Strands workflow tool
        """
        strands_tasks = []

        for task in workflow.tasks:
            # Replace template variables in system_prompt
            system_prompt = task.system_prompt.replace("{PROBLEM_STATEMENT}", problem_statement)
            system_prompt = system_prompt.replace("{TECH_SUPPORT_FILE}", tech_support_file)

            strands_task = {
                "task_id": task.task_id,
                "description": task.description,
                "system_prompt": system_prompt,
                "priority": task.priority,
            }

            # Add optional fields if present
            if task.dependencies:
                strands_task["dependencies"] = task.dependencies

            if task.timeout_minutes:
                strands_task["timeout_minutes"] = task.timeout_minutes

            if task.tools:
                strands_task["tools"] = task.tools

            strands_tasks.append(strands_task)

        return {"workflow_id": workflow.workflow_id, "tasks": strands_tasks}

    @staticmethod
    def load_workflow_for_strands(yaml_file: Path, problem_statement: str = "", tech_support_file: str = "") -> Dict[str, Any]:
        """Load YAML workflow and convert to Strands format in one step.

        Args:
            yaml_file: Path to YAML workflow definition
            problem_statement: Problem statement to inject into task prompts
            tech_support_file: Tech support file path to inject into task prompts

        Returns:
            Dict ready for agent.tool.workflow(action="create", **result)
        """
        workflow = WorkflowLoader.load_from_yaml(yaml_file)
        return WorkflowLoader.to_strands_format(workflow, problem_statement, tech_support_file)

    @staticmethod
    def validate_workflow_yaml(yaml_file: Path) -> bool:
        """Validate YAML workflow without loading.

        Args:
            yaml_file: Path to YAML file to validate

        Returns:
            bool: True if valid, raises exception if invalid
        """
        try:
            WorkflowLoader.load_from_yaml(yaml_file)
            return True
        except Exception as e:
            raise ValueError(f"Invalid workflow YAML: {e}")


def list_available_workflows(workflows_dir: Path) -> List[Path]:
    """List all available workflow YAML files in directory.

    Args:
        workflows_dir: Directory containing workflow YAML files

    Returns:
        List of paths to workflow YAML files
    """
    if not workflows_dir.exists():
        return []

    workflows = []
    for pattern in ["*.yaml", "*.yml"]:
        workflows.extend(workflows_dir.glob(pattern))

    return sorted(workflows)

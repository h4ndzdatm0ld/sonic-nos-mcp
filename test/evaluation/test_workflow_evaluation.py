"""SONiC Workflow-based Evaluation Tests.

Tests using multi-step workflows to evaluate SONiC analysis capabilities.
"""

import pytest
from pathlib import Path


@pytest.mark.evaluation
def test_bgp_authentication_workflow(sonic_workflow_agent, llm_judge_agent, real_tech_support_file):
    """Test BGP authentication troubleshooting workflow.

    Uses techsupport_bgp_md5.tar.gz scenario to test agent's ability to:
    - Diagnose BGP MD5 authentication failures
    - Identify configuration mismatches
    - Provide root cause analysis with evidence
    """
    from .framework.eval_agent_tester import EvalAgentTester

    # Problem statement based on techsupport README scenario
    problem_statement = (
        "BGP neighbor 10.255.0.2 won't establish session on sonic1. "
        "The neighbor appears to be stuck in Active/Connect state. "
        "Investigate and determine root cause."
    )

    # Use BGP-specific techsupport file if available, otherwise default
    test_data_dir = Path(__file__).parent / "data" / "techsupport"
    bgp_file = test_data_dir / "techsupport_bgp_md5.tar.gz"
    tech_support_file = bgp_file if bgp_file.exists() else real_tech_support_file

    # Create evaluator with workflow capability
    evaluator = EvalAgentTester(
        agent=sonic_workflow_agent,
        evaluator_agent=llm_judge_agent,
        test_cases=[],  # Not used for workflow evaluation
        tech_support_file=tech_support_file,
        output_dir=Path("test/evaluation/results/bgp_workflow"),
    )

    # Execute workflow evaluation
    workflow_yaml = Path(__file__).parent / "workflows" / "rca-1.yaml"
    result = evaluator.evaluate_workflow(workflow_yaml, problem_statement, "bgp-authentication")

    # Assert workflow completed successfully
    assert result.passed, f"BGP workflow failed: {result.llm_judge_feedback}"
    assert result.llm_judge_score >= 4, f"BGP workflow score too low: {result.llm_judge_score}/5"

    # Check that MCP tools were used
    assert len(result.used_tools) > 0, "BGP workflow should use MCP tools"

    print(f"✅ BGP Authentication Workflow: Score {result.llm_judge_score}/5")


@pytest.mark.evaluation
def test_syncd_crash_workflow(sonic_workflow_agent, llm_judge_agent, real_tech_support_file):
    """Test syncd container crash troubleshooting workflow.

    Uses techsupport_syncd_crash.tar.gz scenario to test agent's ability to:
    - Identify container crash scenarios
    - Analyze service restart patterns
    - Correlate crash logs with system state
    """
    from .framework.eval_agent_tester import EvalAgentTester

    # Problem statement based on techsupport README scenario
    problem_statement = (
        "ASIC forwarding pipeline keeps failing on sonic1. "
        "Services seem unstable and there are forwarding issues. "
        "Determine what's happening to the dataplane."
    )

    # Use syncd-specific techsupport file if available, otherwise default
    test_data_dir = Path(__file__).parent / "data" / "techsupport"
    syncd_file = test_data_dir / "techsupport_syncd_crash.tar.gz"
    tech_support_file = syncd_file if syncd_file.exists() else real_tech_support_file

    evaluator = EvalAgentTester(
        agent=sonic_workflow_agent,
        evaluator_agent=llm_judge_agent,
        test_cases=[],
        tech_support_file=tech_support_file,
        output_dir=Path("test/evaluation/results/syncd_workflow"),
    )

    workflow_yaml = Path(__file__).parent / "workflows" / "rca-1.yaml"
    result = evaluator.evaluate_workflow(workflow_yaml, problem_statement, "syncd-crash")

    assert result.passed, f"Syncd workflow failed: {result.llm_judge_feedback}"
    assert result.llm_judge_score >= 4, f"Syncd workflow score too low: {result.llm_judge_score}/5"
    assert len(result.used_tools) > 0, "Syncd workflow should use MCP tools"

    print(f"✅ Syncd Crash Workflow: Score {result.llm_judge_score}/5")


@pytest.mark.evaluation
def test_oom_memory_workflow(sonic_workflow_agent, llm_judge_agent, real_tech_support_file):
    """Test OOM/memory exhaustion troubleshooting workflow.

    Uses techsupport_oom.tar.gz scenario to test agent's ability to:
    - Identify memory exhaustion scenarios
    - Analyze reboot patterns and panic-on-OOM configuration
    - Correlate memory pressure with system behavior
    """
    from .framework.eval_agent_tester import EvalAgentTester

    # Problem statement based on techsupport README scenario
    problem_statement = (
        "sonic1 has been experiencing unexpected repeated reboots and service restarts. "
        "Control plane services keep restarting and the system seems unstable. "
        "Find out what's causing the system instability."
    )

    # Use OOM-specific techsupport file if available, otherwise default
    test_data_dir = Path(__file__).parent / "data" / "techsupport"
    oom_file = test_data_dir / "techsupport_oom.tar.gz"
    tech_support_file = oom_file if oom_file.exists() else real_tech_support_file

    evaluator = EvalAgentTester(
        agent=sonic_workflow_agent,
        evaluator_agent=llm_judge_agent,
        test_cases=[],
        tech_support_file=tech_support_file,
        output_dir=Path("test/evaluation/results/oom_workflow"),
    )

    workflow_yaml = Path(__file__).parent / "workflows" / "rca-1.yaml"
    result = evaluator.evaluate_workflow(workflow_yaml, problem_statement, "oom-memory")

    assert result.passed, f"OOM workflow failed: {result.llm_judge_feedback}"
    assert result.llm_judge_score >= 4, f"OOM workflow score too low: {result.llm_judge_score}/5"
    assert len(result.used_tools) > 0, "OOM workflow should use MCP tools"

    print(f"✅ OOM Memory Workflow: Score {result.llm_judge_score}/5")


@pytest.mark.evaluation
def test_simple_mcp_tool_usage(sonic_mcp_tools, sonic_evaluation_agent, real_tech_support_file):
    """Test simple MCP tool usage without LLM evaluation.

    Basic functional verification that agent can use each MCP tool correctly.
    This is a simple smoke test, not a complex workflow evaluation.
    """

    # Test 1: Extract tool
    extract_query = f"Extract this tech support file: {real_tech_support_file}"
    extract_response = sonic_evaluation_agent(extract_query)

    # Verify extract tool was used
    extract_tools = [name for name, metric in extract_response.metrics.tool_metrics.items() if metric.call_count > 0]

    assert "extract_tech_support_file" in extract_tools, "Extract tool should be used"
    print("✅ Extract tool works")

    # Test 2: List tool
    list_query = "List all JSON files in the extracted tech support data"
    list_response = sonic_evaluation_agent(list_query)

    list_tools = [name for name, metric in list_response.metrics.tool_metrics.items() if metric.call_count > 0]

    assert "list_tech_support_files_tool" in list_tools, "List tool should be used"
    print("✅ List tool works")

    # Test 3: Content inspection tool
    content_query = "Show me the contents of any STATE_DB.json file in the tech support data"
    content_response = sonic_evaluation_agent(content_query)

    content_tools = [name for name, metric in content_response.metrics.tool_metrics.items() if metric.call_count > 0]

    assert "get_tech_support_file_content_tool" in content_tools, "Content tool should be used"
    print("✅ Content inspection tool works")

    print("🎉 All 3 MCP tools functional!")


@pytest.mark.evaluation
def test_workflow_yaml_validation():
    """Test that the workflow YAML definition is valid.

    Validates the YAML workflow structure without executing it.
    """
    from .workflow_loader import WorkflowLoader

    workflow_yaml = Path(__file__).parent / "workflows" / "rca-1.yaml"

    # Should not raise exception
    is_valid = WorkflowLoader.validate_workflow_yaml(workflow_yaml)
    assert is_valid, "Workflow YAML should be valid"

    # Load and check structure
    workflow_def = WorkflowLoader.load_from_yaml(workflow_yaml)

    # Verify required fields
    assert workflow_def.workflow_id == "sonic-rca-v1"
    assert len(workflow_def.tasks) == 5  # Should have 5 tasks
    assert workflow_def.tasks[0].task_id == "problem_clarification"
    assert workflow_def.tasks[-1].task_id == "root_cause_determination"

    # Verify task dependencies are correct
    workflow_def.validate_task_dependencies()

    print("✅ Workflow YAML structure is valid")

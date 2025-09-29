"""SONiC Agent Evaluation Tests.

Pytest-based evaluation tests for SONiC network analysis agents using Strands framework.
"""

import pytest


@pytest.mark.evaluation
def test_basic_sonic_analysis(eval_agent_tester_basic):
    """Test basic SONiC analysis capabilities.

    Evaluates the agent's ability to:
    - Extract tech support files
    - Navigate file structures
    - Perform basic content inspection
    """
    results = eval_agent_tester_basic.evaluate_agent("sonic-basic-analysis")

    # Generate detailed report
    report = eval_agent_tester_basic.generate_report(results, "sonic-basic-analysis")
    print(f"\n{report}")

    # Assert all tests pass (will fail with detailed info if not)
    eval_agent_tester_basic.pytest_assert_results(results)


@pytest.mark.evaluation
def test_network_troubleshooting(eval_agent_tester_network):
    """Test network troubleshooting analysis capabilities.

    Evaluates the agent's ability to:
    - Analyze interface status and health
    - Diagnose BGP routing issues
    - Parse system logs for network errors
    - Review configuration files
    - Perform connectivity diagnosis
    """
    results = eval_agent_tester_network.evaluate_agent("sonic-network-troubleshooting")

    # Generate detailed report
    report = eval_agent_tester_network.generate_report(results, "sonic-network-troubleshooting")
    print(f"\n{report}")

    # Assert all tests pass
    eval_agent_tester_network.pytest_assert_results(results)


@pytest.mark.evaluation
def test_tool_selection_accuracy(eval_agent_tester_basic):
    """Test MCP tool selection accuracy specifically.

    Focuses on evaluating whether the agent selects appropriate
    SONiC MCP tools for different types of analysis tasks.
    """
    results = eval_agent_tester_basic.evaluate_agent("sonic-tool-selection")

    # Calculate tool usage metrics
    metrics = eval_agent_tester_basic.calculate_metrics(results)

    print("\n🛠️  Tool Usage Analysis:")
    print(f"   Tool Usage Rate: {metrics.tool_usage_accuracy:.1%}")
    print(f"   Average LLM Score: {metrics.avg_llm_score:.1f}/5")

    # Additional assertion: tool usage rate should be high for basic analysis
    assert metrics.tool_usage_accuracy > 0.8, f"Tool usage rate too low: {metrics.tool_usage_accuracy:.1%}"

    # Assert overall evaluation passes
    eval_agent_tester_basic.pytest_assert_results(results)


@pytest.mark.evaluation
def test_evaluation_framework_metrics(eval_agent_tester_basic):
    """Test that the evaluation framework itself collects proper metrics.

    This meta-test validates the evaluation framework's ability to:
    - Collect response times
    - Track tool usage
    - Calculate pass/fail rates
    - Generate meaningful reports
    """
    results = eval_agent_tester_basic.evaluate_agent("sonic-framework-test")
    metrics = eval_agent_tester_basic.calculate_metrics(results)

    # Validate metrics collection
    assert metrics.total_tests == len(results)
    assert metrics.passed_tests + metrics.failed_tests == metrics.total_tests
    assert metrics.avg_response_time > 0  # Should have some response time
    assert 1 <= metrics.avg_llm_score <= 5  # LLM scores should be in valid range
    assert isinstance(metrics.categories, dict)  # Categories should be tracked

    print("\n📊 Framework Metrics Validation:")
    print(f"   Total Tests: {metrics.total_tests}")
    print(f"   Pass Rate: {metrics.passed_tests/metrics.total_tests*100:.1f}%")
    print(f"   Avg Response Time: {metrics.avg_response_time:.2f}s")
    print(f"   Categories: {list(metrics.categories.keys())}")

    # Framework should pass basic functionality tests
    eval_agent_tester_basic.pytest_assert_results(results)

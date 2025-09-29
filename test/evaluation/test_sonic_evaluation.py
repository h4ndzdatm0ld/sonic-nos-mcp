"""SONiC Agent Evaluation Tests.

Tests that use real LLM agents to evaluate SONiC analysis capabilities
using actual MCP tools and YAML-defined test cases.
"""

import os
import pytest
from pathlib import Path

try:
    from strands import Agent

    STRANDS_AVAILABLE = True
except ImportError:
    Agent = None
    STRANDS_AVAILABLE = False


@pytest.mark.evaluation
@pytest.mark.skipif(
    os.getenv("EXECUTE_EVALUATIONS") != "true", reason="Evaluation tests only run when EXECUTE_EVALUATIONS=true"
)
@pytest.mark.skipif(not STRANDS_AVAILABLE, reason="Strands agents not available for LLM evaluation")
def test_basic_analysis_evaluation(eval_agent_tester_basic):
    """Test basic SONiC analysis scenarios using real LLM agent evaluation."""

    # Run real LLM agent evaluation using the configured tester
    results = eval_agent_tester_basic.evaluate_agent("sonic-basic-analysis")

    # Generate and save report
    report = eval_agent_tester_basic.generate_report(results, "Basic SONiC Analysis")
    print(f"\n{report}")

    # Assert results using pytest integration
    eval_agent_tester_basic.pytest_assert_results(results)


@pytest.mark.evaluation
@pytest.mark.skipif(
    os.getenv("EXECUTE_EVALUATIONS") != "true", reason="Evaluation tests only run when EXECUTE_EVALUATIONS=true"
)
@pytest.mark.skipif(not STRANDS_AVAILABLE, reason="Strands agents not available for LLM evaluation")
def test_network_troubleshooting_evaluation(eval_agent_tester_network):
    """Test network troubleshooting scenarios using real LLM agent evaluation."""

    # Run real LLM agent evaluation using the configured tester
    results = eval_agent_tester_network.evaluate_agent("sonic-network-troubleshooting")

    # Generate and save report
    report = eval_agent_tester_network.generate_report(results, "Network Troubleshooting")
    print(f"\n{report}")

    # Assert results using pytest integration
    eval_agent_tester_network.pytest_assert_results(results)


@pytest.mark.evaluation
def test_simple_mcp_tools():
    """Simple tests for MCP tools without LLM evaluation framework."""

    # Test tech support file extraction
    from sonic_nos_mcp.modules.tech_support.utils.extraction import extract_file

    test_file = Path("test/data/techsupport/techsupport_bgp_md5.tar.gz")
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")

    response = extract_file(file_path=test_file)

    assert response.success is True
    assert response.extract_dir is not None
    assert response.extract_dir.exists()

    # Test file listing
    from sonic_nos_mcp.modules.tech_support.utils.file_listing import list_files

    file_infos = list_files(directory=response.extract_dir)
    assert len(file_infos) > 0

    # Test file reading
    from sonic_nos_mcp.modules.tech_support.utils.text_chunking import chunk_file

    # Find a readable file
    for file_info in file_infos[:5]:  # Check first 5 files
        file_path = response.extract_dir / file_info.path
        if file_path.is_file() and file_path.stat().st_size < 50000:
            chunk = chunk_file(file_path=file_path, page=1)
            assert chunk.content is not None
            break

    # Cleanup
    import shutil

    if response.extract_dir and response.extract_dir.exists():
        shutil.rmtree(response.extract_dir)

"""Pytest fixtures for SONiC agent evaluation testing.

Environment-gated fixtures for Strands agent evaluation with MCP tools.
"""

import os
import yaml
from pathlib import Path
from typing import List

import pytest
from strands import Agent
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters

from .framework.eval_agent_tester import EvaluationCase, EvalAgentTester


@pytest.fixture(scope="session", autouse=True)
def require_evaluation_environment():
    """Session-wide check for evaluation environment variable.

    This fixture runs automatically for all evaluation tests and skips
    the entire test session if EXECUTE_EVALUATIONS is not set to 'true'.
    """
    if os.getenv("EXECUTE_EVALUATIONS") != "true":
        pytest.skip(
            "Evaluation tests require EXECUTE_EVALUATIONS=true. "
            "Set environment variable to run: EXECUTE_EVALUATIONS=true pytest test/evaluation/",
            allow_module_level=True,
        )


@pytest.fixture(scope="session", autouse=True)
def setup_strands_debug_logging():
    """Configure Strands debug logging for evaluation visibility."""
    import logging

    # Configure the root strands logger
    logging.getLogger("strands").setLevel(logging.DEBUG)

    # Add a handler to see the logs
    logging.basicConfig(format="%(levelname)s | %(name)s | %(message)s", handlers=[logging.StreamHandler()])

    print("🔧 Strands debug logging enabled")


@pytest.fixture(scope="session")
def sonic_mcp_client():
    """Create and maintain MCP client session for evaluation tests.

    Returns the active MCP client that agents can use directly.
    """
    try:
        # Install latest code before starting MCP server
        import subprocess

        print("🔄 Installing latest SONiC MCP code...")
        result = subprocess.run(["uv", "pip", "install", "-e", "."], check=True, capture_output=True, text=True)
        print(f"✅ Installation completed: {result.returncode}")

        # Create MCP client with proper session management
        print("🚀 Starting MCP server...")
        client = MCPClient(lambda: stdio_client(StdioServerParameters(command="uv", args=["run", "sonic-nos-mcp"])))
        client.__enter__()  # Start the session
        print("✅ MCP client session started")

        tools = client.list_tools_sync()
        print(f"🔧 Loaded {len(tools)} SONiC MCP tools for evaluation")

        # Print available tools for debugging
        for i, tool in enumerate(tools):
            tool_info = getattr(tool, "name", f"tool_{i}")
            print(f"   - {tool_info}: {str(type(tool))}")

        yield client

        # Cleanup
        client.__exit__(None, None, None)
        print("🛑 MCP client session closed")

    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e.stdout} {e.stderr}")
        pytest.skip(f"Failed to install SONiC MCP server: {e}")
    except Exception as e:
        print(f"❌ MCP connection failed: {e}")
        pytest.skip(f"Failed to connect to SONiC MCP server: {e}")


@pytest.fixture(scope="session")
def sonic_evaluation_agent(sonic_mcp_client):
    """SONiC analysis agent with Sonnet 4 v1:0 for evaluation."""
    tools = sonic_mcp_client.list_tools_sync()

    return Agent(
        model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        system_prompt="""
        You are an expert SONiC network operating system analyst. Your role is to analyze 
        SONiC tech support files to diagnose network issues, system health, and configuration problems.
        
        Key capabilities:
        - Extract and examine SONiC tech support archives
        - Navigate file structures efficiently  
        - Analyze system databases (STATE_DB, CONFIG_DB, etc.)
        - Interpret system logs and error messages
        - Identify network connectivity and routing issues
        - Provide actionable diagnostic insights
        
        Always use the appropriate MCP tools for file extraction, listing, and content analysis.
        Provide thorough analysis with specific findings and recommendations.
        """,
        tools=tools,
        record_direct_tool_call=True,
    )


@pytest.fixture(scope="session")
def sonic_workflow_agent(sonic_mcp_client):
    """SONiC workflow coordination agent with Sonnet 4 v1:0 and workflow tool."""
    tools = sonic_mcp_client.list_tools_sync()

    try:
        from strands_tools import workflow

        tools = tools + [workflow]
    except ImportError:
        pass

    return Agent(
        model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        system_prompt="""
        You are an expert SONiC network analyst capable of coordinating multi-step analysis workflows.

        Your role is to execute structured troubleshooting workflows for SONiC tech support analysis:
        - Coordinate multiple analysis tasks in logical sequence
        - Use workflow tool to manage multi-step processes
        - Ensure each workflow step builds on previous findings
        - Integrate MCP tools for SONiC tech support file analysis
        - Provide comprehensive root cause analysis

        When executing workflows, follow the defined task sequence and ensure
        each step provides meaningful input to the next step.
        """,
        tools=tools,
        record_direct_tool_call=True,
    )


@pytest.fixture(scope="session")
def llm_judge_agent():
    """LLM judge agent using Sonnet 4 v1:0 for qualitative evaluation."""
    return Agent(
        model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        system_prompt="""
        You are an expert evaluator of SONiC network analysis responses. Your job is to assess 
        the quality of AI agent responses for SONiC tech support file analysis.
        
        Evaluation criteria:
        1. Accuracy - factual correctness of SONiC network analysis
        2. Relevance - how well the response addresses the specific query
        3. Completeness - thoroughness of analysis and coverage of important aspects
        4. Tool Usage - appropriate selection and effective use of available MCP tools
        
        Consider the following in your evaluation:
        - SONiC-specific knowledge (interfaces, databases, system structure)
        - Network troubleshooting methodology  
        - Appropriate use of tech support data extraction and analysis tools
        - Actionable insights and recommendations
        
        Score each response from 1-5 where:
        - 5: Excellent - comprehensive, accurate, uses tools appropriately
        - 4: Good - solid analysis with minor gaps
        - 3: Adequate - basic analysis but missing key elements
        - 2: Poor - significant gaps or inaccuracies
        - 1: Unacceptable - incorrect or irrelevant response
        
        Always format your response as:
        SCORE: X
        FEEDBACK: Detailed explanation of your assessment
        """,
    )


def load_test_cases_from_yaml(yaml_file: Path) -> List[EvaluationCase]:
    """Load test cases from YAML file."""
    with open(yaml_file, "r") as f:
        data = yaml.safe_load(f)

    cases = []
    for case_data in data.get("test_cases", []):
        case = EvaluationCase(
            id=case_data["id"],
            query=case_data["query"],
            category=case_data["category"],
            expected=case_data.get("expected"),
            expected_tools=case_data.get("expected_tools", []),
            expected_patterns=case_data.get("expected_patterns", []),
            context=case_data.get("context", {}),
        )
        cases.append(case)

    return cases


@pytest.fixture
def basic_analysis_test_cases():
    """Load basic analysis test cases from YAML."""
    yaml_file = Path(__file__).parent / "test_cases" / "basic_analysis.yaml"
    return load_test_cases_from_yaml(yaml_file)


@pytest.fixture
def network_troubleshooting_test_cases():
    """Load network troubleshooting test cases from YAML."""
    yaml_file = Path(__file__).parent / "test_cases" / "network_troubleshooting.yaml"
    return load_test_cases_from_yaml(yaml_file)


@pytest.fixture
def eval_agent_tester_basic(sonic_evaluation_agent, llm_judge_agent, basic_analysis_test_cases, real_tech_support_file):
    """EvalAgentTester configured for basic analysis tests."""
    return EvalAgentTester(
        agent=sonic_evaluation_agent,
        evaluator_agent=llm_judge_agent,
        test_cases=basic_analysis_test_cases,
        tech_support_file=real_tech_support_file,
        output_dir=Path("test/evaluation/results/basic_analysis"),
    )


@pytest.fixture
def eval_agent_tester_network(
    sonic_evaluation_agent, llm_judge_agent, network_troubleshooting_test_cases, real_tech_support_file
):
    """EvalAgentTester configured for network troubleshooting tests."""
    return EvalAgentTester(
        agent=sonic_evaluation_agent,
        evaluator_agent=llm_judge_agent,
        test_cases=network_troubleshooting_test_cases,
        tech_support_file=real_tech_support_file,
        output_dir=Path("test/evaluation/results/network_troubleshooting"),
    )

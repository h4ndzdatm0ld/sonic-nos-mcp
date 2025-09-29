#!/usr/bin/env python3
"""Manual SONiC MCP Agent Workflow Invoker

This script allows you to manually invoke the SONiC MCP agent workflow with custom prompts.
Based on the debug_tool_detection.py script but with command-line interface and logging.

# Basic usage
< Make sure to have AWS Creds set up >

# BGP issue
uv run hatch run test:python examples/invokeWorkflow.py \
  --workflow test/evaluation/workflows/rca-1.yaml \
  --prompt "A routing peer at 10.255.0.2 keeps flapping against sonic1. Inspect this tech-support archive and tell me why the session won't stay established, pointing to the evidence you use." \
  --tech-support-file test/data/techsupport/techsupport_bgp_md5.tar.gz \
  --verbose
"""

import sys
import os
import argparse
import logging
import traceback
from pathlib import Path
from datetime import datetime
from typing import Union

sys.path.append(".")
sys.path.append("test")

try:
    from strands import Agent
    from strands.agent.conversation_manager import SlidingWindowConversationManager
    from strands.models.bedrock import BedrockModel
    from strands.tools.mcp import MCPClient
    from mcp import stdio_client, StdioServerParameters

    STRANDS_AVAILABLE = True
except ImportError as e:
    print(f"❌ Strands import error: {e}")
    STRANDS_AVAILABLE = False

try:
    from strands_tools import workflow
    from evaluation.workflow_loader import WorkflowLoader

    WORKFLOW_AVAILABLE = True
except ImportError as e:
    print(f"❌ Workflow import error: {e}")
    WORKFLOW_AVAILABLE = False


def setup_logging() -> str:
    """Set up logging to file and return the log file path."""
    logs_dir = Path("examples/logs")
    logs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"manual_workflow_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )

    return str(log_file)


def manual_agent_workflow(
    prompt: str,
    tech_support_file: Union[str, None] = None,
    workflow_file: Union[str, None] = None,
    verbose: bool = False,
) -> None:
    """Execute the SONiC MCP agent workflow with the provided prompt."""
    logger = logging.getLogger(__name__)
    logger.info("🔍 Starting SONiC MCP agent workflow...")

    if not tech_support_file:
        logger.error("❌ Tech support file is required for SONiC analysis")
        raise ValueError("--tech-support-file parameter is required")

    tech_support_path = Path(tech_support_file)
    if not tech_support_path.exists():
        logger.error(f"❌ Tech support file not found: {tech_support_file}")
        raise FileNotFoundError(f"Tech support file not found: {tech_support_file}")

    logger.info(f"✅ Tech support file validated: {tech_support_path}")

    if not STRANDS_AVAILABLE:
        logger.error("❌ Strands dependencies not available")
        logger.error("Make sure you're running in the correct environment with: uv run hatch run test:python")
        return

    logger.info("✅ Strands imports successful")

    logger.info("🔧 Setting up MCP client...")

    os.system("uv sync > /dev/null 2>&1")
    logger.info("✅ UV sync completed")

    try:
        client = MCPClient(lambda: stdio_client(StdioServerParameters(command="uv", args=["run", "sonic-nos-mcp"])))
        client.__enter__()
        logger.info("✅ MCP client created and started")

        tools = client.list_tools_sync()
        logger.info(f"🔧 Loaded {len(tools)} SONiC MCP tools")

        if not workflow_file:
            logger.error("❌ Workflow file is required")
            raise ValueError("--workflow parameter is required")

        if not WORKFLOW_AVAILABLE:
            logger.error("❌ Workflow functionality not available")
            raise ImportError("strands_tools.workflow not available in this environment")

        logger.info(f"🔄 Loading workflow from: {workflow_file}")

        workflow_config = WorkflowLoader.load_workflow_for_strands(Path(workflow_file), prompt, tech_support_file)
        logger.info(f"📋 Workflow: {workflow_config['workflow_id']} ({len(workflow_config['tasks'])} tasks)")
        logger.info(f"Tech support file passed to workflow: {tech_support_file}")

        logger.info("🔧 Creating conversation manager with sliding window...")
        conversation_manager = SlidingWindowConversationManager(
            window_size=20,  # Maximum number of messages to keep
            should_truncate_results=True, # Enable truncating tool result when a message is too large for the model's context window
        )

        logger.info("🔧 Creating custom model with max_tokens configuration...")
        custom_model = BedrockModel(
            model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
            max_tokens=16384  # Increase from default to handle longer workflows
        )
        logger.info(f"Created model with config: {custom_model.config}")

        agent = Agent(
            model=custom_model,
            tools=tools + [workflow],
            conversation_manager=conversation_manager
        )
        logger.info("✅ Workflow agent created with sliding window conversation manager and custom max_tokens")

        logger.info("🔧 Creating workflow...")
        agent.tool.workflow(action="create", **workflow_config)

        user_input = f"Problem: {prompt}\nTech support file: {tech_support_file}"
        logger.info(f"Workflow will analyze: {tech_support_file}")

        logger.info("▶️ Starting workflow execution...")
        agent.tool.workflow(action="start", workflow_id=workflow_config["workflow_id"], user_input=user_input)

        logger.info("⏳ Checking workflow status...")
        response = agent.tool.workflow(action="status", workflow_id=workflow_config["workflow_id"])

        logger.info("✅ Response received")
        logger.info(f"Response type: {type(response)}")

        if verbose:
            logger.info("=== VERBOSE RESPONSE DETAILS ===")
            response_attrs = [attr for attr in dir(response) if not attr.startswith("_")]
            for attr in response_attrs:
                logger.info(f"  - {attr}: {type(getattr(response, attr, None))}")

        if hasattr(response, "metrics"):
            logger.info("=== TOOL USAGE ANALYSIS ===")
            for tool_name, tool_metric in response.metrics.tool_metrics.items():
                logger.info(f"  🔧 {tool_name}: {tool_metric.call_count} calls ({tool_metric.total_time:.2f}s)")

        logger.info("=== AGENT RESPONSE ===")
        response_str = str(response)
        logger.info(response_str)

        print("\n" + "=" * 60)
        print("AGENT RESPONSE:")
        print("=" * 60)
        print(response_str)
        print("=" * 60)

    except Exception as e:
        logger.error(f"❌ Error during execution: {e}")
        logger.error("Full traceback:")
        logger.error(traceback.format_exc())

    finally:
        try:
            client.__exit__(None, None, None)
            logger.info("🛑 MCP client session closed")
        except:
            pass


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Manual SONiC MCP Agent Invoker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Multi-step workflow execution
  uv run hatch run test:python examples/invokeWorkflow.py \\
    --workflow test/evaluation/workflows/rca-1.yaml \\
    --prompt "BGP neighbor 10.255.0.2 won't establish session" \\
    --tech-support-file test/data/techsupport/sonic_dump_sonic_20250927_164055.tar.gz \\
    --verbose
        """,
    )

    parser.add_argument("--prompt", required=True, help="The problem statement/query for analysis")

    parser.add_argument("--tech-support-file", required=True, help="Path to SONiC tech support file to analyze")

    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed response analysis and debugging information"
    )

    parser.add_argument(
        "--workflow",
        required=True,
        help="Path to YAML workflow file for multi-step execution",
    )

    args = parser.parse_args()

    log_file_path = setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("🚀 SONiC MCP Manual Agent Invoker")
    logger.info(f"📝 Prompt: {args.prompt}")
    if args.tech_support_file:
        logger.info(f"📁 Tech support file: {args.tech_support_file}")
    if args.workflow:
        logger.info(f"🔄 Workflow file: {args.workflow}")
    logger.info(f"🔧 Verbose mode: {args.verbose}")

    manual_agent_workflow(
        prompt=args.prompt, tech_support_file=args.tech_support_file, workflow_file=args.workflow, verbose=args.verbose
    )

    print(f"\n📁 Log saved to: {log_file_path}")


if __name__ == "__main__":
    main()

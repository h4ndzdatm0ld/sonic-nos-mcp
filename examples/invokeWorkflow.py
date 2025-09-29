#!/usr/bin/env python3
"""SONiC MCP RCA Workflow Invoker

This script provides a command-line interface to invoke the SONiC RCA workflow
using the simplified sequential agent approach.
"""

import sys
import argparse
import logging
import traceback
from pathlib import Path
from datetime import datetime

# Import the RCA workflow function
from rca import rca_workflow


def setup_logging() -> str:
    """Set up logging to file and return the log file path."""
    # Create logs directory relative to script location
    script_dir = Path(__file__).parent
    logs_dir = script_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"rca_workflow_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )

    return str(log_file)


def invoke_rca_workflow(
    problem_statement: str,
    tech_support_file: str,
    verbose: bool = False,
) -> None:
    """Execute the SONiC RCA workflow with the provided problem statement."""
    logger = logging.getLogger(__name__)
    logger.info("🔍 Starting SONiC RCA workflow...")

    if not tech_support_file:
        logger.error("❌ Tech support file is required for SONiC analysis")
        raise ValueError("--tech-support-file parameter is required")

    tech_support_path = Path(tech_support_file)
    if not tech_support_path.exists():
        logger.error(f"❌ Tech support file not found: {tech_support_file}")
        raise FileNotFoundError(f"Tech support file not found: {tech_support_file}")

    logger.info(f"✅ Tech support file validated: {tech_support_path}")

    try:
        logger.info("🚀 Starting 5-step SONiC RCA workflow...")

        # Execute the sequential RCA workflow
        result = rca_workflow(problem_statement, tech_support_file)

        logger.info("✅ RCA workflow completed successfully")

        print("\n" + "=" * 80)
        print("🎯 FINAL ROOT CAUSE ANALYSIS:")
        print("=" * 80)
        print(result)
        print("=" * 80)

        if verbose:
            logger.info("=== VERBOSE OUTPUT ===")
            logger.info(f"Problem: {problem_statement}")
            logger.info(f"Tech file: {tech_support_file}")
            logger.info("RCA workflow completed successfully")

    except Exception as e:
        logger.error(f"❌ Error during RCA workflow execution: {e}")
        logger.error("Full traceback:")
        logger.error(traceback.format_exc())
        raise


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="SONiC RCA Workflow Invoker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # BGP routing issue
  python examples/invokeWorkflow.py \\
    --prompt "BGP neighbor 10.255.0.2 keeps flapping and won't establish session" \\
    --tech-support-file test/data/techsupport/techsupport_bgp_md5.tar.gz \\
    --verbose

  # Memory/OOM issue
  python examples/invokeWorkflow.py \\
    --prompt "System experiencing out of memory conditions" \\
    --tech-support-file test/data/techsupport/techsupport_oom.tar.gz

  # System crash issue
  python examples/invokeWorkflow.py \\
    --prompt "syncd process keeps crashing" \\
    --tech-support-file test/data/techsupport/techsupport_syncd_crash.tar.gz
        """,
    )

    parser.add_argument("--prompt", required=True, help="The problem statement/query for SONiC RCA analysis")

    parser.add_argument("--tech-support-file", required=True, help="Path to SONiC tech support file to analyze")

    parser.add_argument("--verbose", action="store_true", help="Show detailed logging and debugging information")

    args = parser.parse_args()

    log_file_path = setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("🚀 SONiC RCA Workflow Invoker")
    logger.info(f"📝 Problem: {args.prompt}")
    logger.info(f"📁 Tech support file: {args.tech_support_file}")
    logger.info(f"🔧 Verbose mode: {args.verbose}")

    try:
        invoke_rca_workflow(
            problem_statement=args.prompt, tech_support_file=args.tech_support_file, verbose=args.verbose
        )
        print(f"\n📁 Log saved to: {log_file_path}")

    except Exception as e:
        logger.error(f"❌ RCA workflow failed: {e}")
        print(f"\n📁 Error log saved to: {log_file_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()

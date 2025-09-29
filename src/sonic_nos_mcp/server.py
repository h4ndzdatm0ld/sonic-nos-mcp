"""SONiC NOS MCP Server implementation.

This module implements a unified Model Context Protocol (MCP) server that provides
access to various SONiC tools from different modules. It dynamically loads and registers
tools from all available modules using a plugin architecture.
"""

import argparse
import logging
import sys
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from sonic_nos_mcp.module_registry import ModuleRegistry

# Import modules to trigger automatic registration through side effects
from sonic_nos_mcp.modules.tech_support import module as tech_support_module  # noqa: F401

logger = logging.getLogger(__name__)


class SonicNosMcpServer:
    """SONiC NOS MCP Server that hosts multiple modules.

    This server provides a unified interface for all SONiC NOS MCP tools
    from various modules. It dynamically discovers and loads tools
    from all available modules using a plugin architecture.

    Attributes:
        mcp: FastMCP instance that handles tool registration and execution
    """

    def __init__(self) -> None:
        """Initialize the server with all modules."""
        logger.info("Initializing SONiC NOS MCP Server")
        self.mcp = FastMCP("sonic-nos-mcp-server", log_level="ERROR")

        logger.info("Loading registered modules")
        self._load_modules()

        logger.info("Server initialization complete")

    def _load_modules(self) -> None:
        """Load all registered modules and register their tools."""
        modules = ModuleRegistry.get_modules()
        logger.info("Found %d registered modules", len(modules))

        for module_class in modules:
            module_name = module_class.get_name()
            logger.info("Loading module: %s", module_name)

            try:
                logger.debug(f"Creating instance of module class: {module_class.__name__}")
                module = module_class()

                logger.debug(f"Registering tools for module: {module_name}")
                module.register_tools(self.mcp)
                logger.info("Successfully loaded module: %s", module_name)

            except Exception as e:
                logger.exception("Failed to load module %s: %s", module_name, str(e))

    def run(self, transport: Annotated[str, Field(description="Transport to use (stdio or http)")] = "stdio") -> None:
        """Run the server with the specified transport mechanism.

        Args:
            transport: Transport to use (stdio or http)
        """
        logger.info("Starting server with transport: %s", transport)
        self.mcp.run(transport=transport)


def main() -> None:
    """Run the SONiC NOS MCP Server.

    This function initializes and starts the server, handling any exceptions
    that might occur during startup or operation.
    """
    # Parse command line arguments FIRST - before any heavy initialization
    parser = argparse.ArgumentParser(
        prog="sonic-nos-mcp",
        description="SONiC Network Operating System MCP Server - Tools for SONiC network device analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start MCP server (for MCP client integration)
  sonic-nos-mcp

  # Run with HTTP transport (development)
  sonic-nos-mcp --transport http

  # Show version information
  sonic-nos-mcp --version

Available Tools:
  • extract_tech_support_file    - Extract SONiC tech support archives
  • list_tech_support_files_tool - List files in extracted archives
  • get_tech_support_file_content_tool - Read and search file contents

Available Resources:
  • sonic://tech-support-guide   - Comprehensive SONiC analysis guide

Usage with MCP Clients:
  Configure your MCP client to run: uvx sonic-nos-mcp
  or use Docker: docker run -i sonic-nos-mcp:latest

Installation:
  # Install and run with uvx
  uvx sonic-nos-mcp

  # Or install from local directory
  uvx --from . sonic-nos-mcp

  # Or run with Docker
  docker run --rm -i sonic-nos-mcp:latest
        """,
    )

    parser.add_argument(
        "--version", "-v", action="version", version="sonic-nos-mcp 1.0.0", help="Show version information"
    )

    parser.add_argument(
        "--transport", "-t", choices=["stdio", "http"], default="stdio", help="Transport mechanism (default: stdio)"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="ERROR",
        help="Set logging level (default: ERROR)",
    )

    # Parse arguments - this handles --help and --version automatically
    args = parser.parse_args()

    # Configure logging based on parsed arguments
    logging.basicConfig(
        level=getattr(logging, args.log_level), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Only NOW initialize the server (after argument parsing is complete)
    try:
        logger.info("Starting SONiC NOS MCP Server with transport: %s", args.transport)
        server = SonicNosMcpServer()
        server.run(transport=args.transport)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.exception("Server failed with error: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()

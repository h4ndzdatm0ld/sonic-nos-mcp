"""Tech Support module implementation.

This module provides tools for working with tech support files.
"""

import logging
from pathlib import Path
from typing import Annotated, Optional

import yaml
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from sonic_nos_mcp.module_base import ModuleBase
from sonic_nos_mcp.module_registry import ModuleRegistry
from sonic_nos_mcp.modules.tech_support.models.extraction_models import ExtractTechSupportRequest
from sonic_nos_mcp.modules.tech_support.models.file_listing_models import ListTechSupportFilesRequest
from sonic_nos_mcp.modules.tech_support.models.text_chunking_models import GetTechSupportFileContentRequest
from sonic_nos_mcp.modules.tech_support.tools.extract_tool import extract_tech_support
from sonic_nos_mcp.modules.tech_support.tools.inspect_tool import read_tech_support_file_content
from sonic_nos_mcp.modules.tech_support.tools.list_tool import list_tech_support_files

logger = logging.getLogger(__name__)


class TechSupportModule(ModuleBase):
    """Module for tech support file analysis."""

    def register_tools(self, mcp: FastMCP) -> None:
        """Register all tech support tools with the MCP server."""
        logger.info("Registering tech support tools and resources")

        # Register resource with exception handling
        try:

            @mcp.resource(
                "sonic://tech-support-guide",
                description="Comprehensive guide for analyzing SONiC network device tech support files",
            )
            def get_sonic_tech_support_guide() -> str:
                """Provides comprehensive guide to SONiC tech support file structure and analysis."""
                try:
                    module_dir = Path(__file__).parent
                    resource_path = module_dir / "resources" / "tech-support.yaml"
                    logger.debug(f"Loading resource from: {resource_path}")

                    if resource_path.exists():
                        with open(resource_path, "r") as f:
                            resource_data = yaml.safe_load(f)
                        logger.info(f"Loaded tech support guide: {resource_data.get('title', 'Unknown')}")

                        content = resource_data.get("content")
                        if not content:
                            logger.error("No content found in YAML resource")
                            raise ValueError("No content found in YAML resource")
                        return content
                    else:
                        logger.error(f"Resource file not found: {resource_path}")
                        raise FileNotFoundError(f"YAML resource file not found at {resource_path}")

                except Exception as e:
                    logger.exception(f"Failed to load YAML resource: {e}")
                    raise

            logger.debug("Successfully registered tech support guide resource")
        except Exception as e:
            logger.error(f"Failed to register tech support guide resource: {e}")

        # Register extract tool with exception handling
        try:

            @mcp.tool(
                description="""
            Extract a tech support file to a temporary directory.

            This tool takes a tech support archive file (tar.gz, zip, etc.) and extracts its contents
            to a temporary directory for analysis. Tech support files contain logs, configuration files,
            and other diagnostic information from SONIC network devices.

            ⚠️ IMPORTANT: Pay close attention to the returned `extract_dir` path - this is CRITICAL for all subsequent analysis!

            The `extract_dir` returned by this tool is your entry point to all extracted tech support data.
            You MUST use this extracted directory path with:
            - list_tech_support_files_tool: To browse and filter files in the extracted directory
            - read_tech_support_file: To read and analyze specific files using paths relative to extract_dir

            WORKFLOW: Extract → Note extract_dir path → List files → Read specific files

            After extraction is complete, the tool automatically returns a list of all files
            in the extracted directory, eliminating the need for a separate call to list files.
            However, for detailed analysis you should use the extract_dir path with other tools.

            The extraction process handles various archive formats including .zip, .tar.gz, .tgz, etc.

            SONIC tech support files typically contain the following key directories:
            - /dump: Contains system state dumps including network configuration, interface status, routing tables,
                     database dumps (CONFIG_DB.json, STATE_DB.json, etc.), and hardware information
            - /log: System logs including syslog, container logs, and application-specific logs
            - /proc: Linux procfs information including network statistics, system information, and kernel parameters
            - /etc: System configuration files
            - /sai: Switch Abstraction Interface configuration and state
            - /warmboot: Warm boot related state and configuration files

            Key files to examine (paths relative to extract_dir):
            - dump/version: Shows SONiC version, platform, ASIC, and uptime information
            - dump/CONFIG_DB.json: Network configuration database
            - dump/interface.status: Status of all network interfaces
            - dump/ip.route: IP routing table
            - dump/docker.ps: Container status
            - log/syslog*: System logs
            - proc/net/vlan/: VLAN configuration and statistics

            REMEMBER: All file operations after extraction must use the returned extract_dir as the base path!
            """
            )
            def extract_tech_support_file(
                file_path: Annotated[str, Field(description="Path to the tech support file to extract")],
                temp_dir: Annotated[
                    Optional[str],
                    Field(
                        description="Optional path to temporary directory. If not provided, a system temp directory will be used."
                    ),
                ] = None,
            ):
                """Extract a tech support file to a temporary directory."""
                logger.info(f"Tool called: extract_tech_support_file with file_path={file_path}, temp_dir={temp_dir}")

                request = ExtractTechSupportRequest(
                    file_path=file_path,
                    temp_dir=temp_dir,
                    remove_archives=True,
                )
                response = extract_tech_support(request)

                result = {
                    "extract_dir": response.extract_dir,
                    "success": response.success,
                    "error_message": response.error_message,
                    "files": response.files,
                }

                logger.info(f"Tool extract_tech_support_file completed with success={response.success}")
                return result

            logger.debug("Successfully registered extract_tech_support_file tool")
        except Exception as e:
            logger.error(f"Failed to register extract_tech_support_file tool: {e}")

        # Register list tool with exception handling
        try:

            @mcp.tool(
                description="""
            List all files in the extracted tech support directory with optional pattern filtering.

            This tool provides a comprehensive listing of all files and directories within an extracted
            tech support archive. You can optionally filter the results using glob patterns to find
            specific types of files or directories.

            Common glob patterns:
            - "*.json": Find all JSON database files
            - "dump/*": Find all files in the dump directory
            - "*log*": Find all files with 'log' in the name
            - "*/CONFIG_DB*": Find CONFIG_DB files in any directory

            This tool is automatically called after extraction, but can also be used independently
            to re-examine the file structure or apply different filtering patterns.
            """
            )
            def list_tech_support_files_tool(
                extract_dir: Annotated[
                    str, Field(description="Path to the directory containing extracted tech support files")
                ],
                pattern: Annotated[Optional[str], Field(description="Optional glob pattern to filter files")] = None,
            ):
                """List all files in the extracted tech support directory."""
                logger.info(
                    f"Tool called: list_tech_support_files_tool with extract_dir={extract_dir}, pattern={pattern}"
                )

                request = ListTechSupportFilesRequest(
                    extract_dir=extract_dir,
                    pattern=pattern,
                )
                response = list_tech_support_files(request)

                files = []
                for file_info in response.files:
                    files.append(
                        {
                            "path": file_info.path,
                            "is_directory": file_info.is_directory,
                        }
                    )

                result = {
                    "files": files,
                    "success": response.success,
                    "error_message": response.error_message,
                }

                logger.info(
                    f"Tool list_tech_support_files_tool completed with success={response.success}, found {len(files)} files"
                )
                return result

            logger.debug("Successfully registered list_tech_support_files_tool")
        except Exception as e:
            logger.error(f"Failed to register list_tech_support_files_tool: {e}")

        # Register read tool with exception handling
        try:

            @mcp.tool(
                description="""
            Read SONiC tech support files with chunking and pattern matching.

            This tool reads files from extracted tech support archives and returns content
            in manageable chunks. Chunk size is controlled by the MCP_SONIC_TECH_SUPPORT_CHUNK_SIZE
            environment variable (default: 10000 characters).

            Usage modes:
            - Simple reading: Just specify file_path for paginated content
            - Pattern search: Add pattern parameter for regex-based content extraction

            Common SONiC files:
            - show/bgp/summary: BGP neighbor status
            - config_db.json: Device configuration
            - syslog: System logs
            - dump/docker.ps: Container status
            - dump/version: SONiC version and platform info
            """
            )
            def read_tech_support_file(
                file_path: Annotated[str, Field(description="Path to the file to read")],
                pattern: Annotated[
                    Optional[str], Field(description="Optional regex pattern to extract specific content from the file")
                ] = None,
                page: Annotated[int, Field(description="Page number to retrieve (starting from 1)")] = 1,
                chunk_size: Annotated[
                    Optional[str],
                    Field(description="Optional chunk size in characters. Overrides environment variable."),
                ] = None,
            ):
                """Read SONiC tech support files with chunking."""
                logger.info(
                    f"Tool called: read_tech_support_file with file_path={file_path}, pattern={pattern}, page={page}"
                )

                try:
                    request = GetTechSupportFileContentRequest(
                        file_path=str(file_path),
                        pattern=pattern,
                        chunk_size=chunk_size,
                        page=page,
                    )
                    response = read_tech_support_file_content(request)
                except Exception as e:
                    logger.exception(f"Error creating request or getting file content: {str(e)}")
                    return {
                        "content": f"Error: {str(e)}",
                        "matches": [],
                        "page": 1,
                        "total_pages": 1,
                        "file_path": str(file_path),
                        "success": False,
                        "error_message": f"Failed to get file content: {str(e)}",
                    }

                result = {
                    "content": response.content,
                    "matches": response.matches,
                    "page": response.page,
                    "total_pages": response.total_pages,
                    "file_path": response.file_path,
                    "success": response.success,
                    "error_message": response.error_message,
                }

                logger.info(
                    f"Tool read_tech_support_file completed with success={response.success}, "
                    f"page {response.page}/{response.total_pages}, found {len(response.matches)} matches"
                )
                return result

            logger.debug("Successfully registered read_tech_support_file tool")
        except Exception as e:
            logger.error(f"Failed to register read_tech_support_file tool: {e}")

        logger.info("Completed tech support tools registration")


logger.info("Registering TechSupportModule with registry")
ModuleRegistry.register(TechSupportModule)

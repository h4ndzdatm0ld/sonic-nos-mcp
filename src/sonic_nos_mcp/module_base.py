"""Base class for all MCP modules.

This module defines the abstract base class that all MCP modules must inherit from.
It provides a standardized interface for module registration and tool management.
"""

from abc import ABC, abstractmethod

from mcp.server.fastmcp import FastMCP


class ModuleBase(ABC):
    """Base class for all MCP modules.

    All modules must inherit from this class and implement the register_tools method.
    """

    @abstractmethod
    def register_tools(self, mcp: FastMCP) -> None:
        """Register all tools provided by this module with the MCP server.

        Args:
            mcp: The FastMCP instance to register tools with
        """
        pass

    @classmethod
    def get_name(cls) -> str:
        """Get the name of this module.

        The default implementation converts the class name to snake_case
        and removes any '_module' suffix if present.

        Returns:
            str: The module name in snake_case format
        """
        return cls.__name__

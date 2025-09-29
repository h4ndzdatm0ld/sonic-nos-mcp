"""Registry for MCP modules.

This module provides a registry for all MCP modules. It allows modules to
register themselves and provides methods to retrieve registered modules.
"""

from typing import Dict, List, Type

from .module_base import ModuleBase


class ModuleRegistry:
    """Registry for MCP modules.

    This class maintains a registry of all available modules.
    """

    _instance = None
    _modules: Dict[str, Type[ModuleBase]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModuleRegistry, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, module_class: Type[ModuleBase]) -> None:
        """Register a module class.

        Args:
            module_class: The module class to register
        """
        module_name = module_class.get_name()
        cls._modules[module_name] = module_class

    @classmethod
    def get_modules(cls) -> List[Type[ModuleBase]]:
        """Get all registered modules.

        Returns:
            List[Type[ModuleBase]]: List of registered module classes
        """
        return list(cls._modules.values())

    @classmethod
    def get_module(cls, name: str) -> Type[ModuleBase]:
        """Get a specific module by name.

        Args:
            name: The name of the module to retrieve

        Returns:
            Type[ModuleBase]: The module class

        Raises:
            KeyError: If the module is not registered
        """
        if name not in cls._modules:
            raise KeyError(f"Module '{name}' not registered")
        return cls._modules[name]

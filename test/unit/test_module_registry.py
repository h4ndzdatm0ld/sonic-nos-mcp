"""Unit tests for module_registry."""

import pytest

from sonic_nos_mcp.module_registry import ModuleRegistry
from sonic_nos_mcp.module_base import ModuleBase


class TestModuleRegistry:
    """Test ModuleRegistry functionality."""

    def setup_method(self):
        """Reset registry before each test."""
        ModuleRegistry._modules = {}

    def teardown_method(self):
        """Clean up registry after each test."""
        ModuleRegistry._modules = {}

    def test_register_module_class(self):
        """Test registering a module class."""

        class TestModule(ModuleBase):
            @classmethod
            def get_name(cls):
                return "test_module"

            def register_tools(self, mcp):
                pass

        # Register the module class
        ModuleRegistry.register(TestModule)

        # Verify it was registered
        modules = ModuleRegistry.get_modules()
        assert len(modules) == 1
        assert modules[0] is TestModule

    def test_register_multiple_module_classes(self):
        """Test registering multiple module classes."""

        class Module1(ModuleBase):
            @classmethod
            def get_name(cls):
                return "module1"

            def register_tools(self, mcp):
                pass

        class Module2(ModuleBase):
            @classmethod
            def get_name(cls):
                return "module2"

            def register_tools(self, mcp):
                pass

        # Register both modules
        ModuleRegistry.register(Module1)
        ModuleRegistry.register(Module2)

        # Verify both were registered
        modules = ModuleRegistry.get_modules()
        assert len(modules) == 2
        assert Module1 in modules
        assert Module2 in modules

    def test_get_module_by_name(self):
        """Test retrieving specific module by name."""

        class TestModule(ModuleBase):
            @classmethod
            def get_name(cls):
                return "named_module"

            def register_tools(self, mcp):
                pass

        ModuleRegistry.register(TestModule)

        # Get module by name
        retrieved_module = ModuleRegistry.get_module("named_module")
        assert retrieved_module is TestModule

    def test_get_module_nonexistent(self):
        """Test getting non-existent module raises KeyError."""
        with pytest.raises(KeyError, match="Module 'nonexistent' not registered"):
            ModuleRegistry.get_module("nonexistent")

    def test_register_same_module_name_twice(self):
        """Test registering modules with same name (should overwrite)."""

        class TestModule1(ModuleBase):
            @classmethod
            def get_name(cls):
                return "duplicate_name"

            def register_tools(self, mcp):
                pass

        class TestModule2(ModuleBase):
            @classmethod
            def get_name(cls):
                return "duplicate_name"

            def register_tools(self, mcp):
                pass

        # Register both modules with same name
        ModuleRegistry.register(TestModule1)
        ModuleRegistry.register(TestModule2)

        # Second one should overwrite the first
        modules = ModuleRegistry.get_modules()
        assert len(modules) == 1
        assert modules[0] is TestModule2  # Should be the latest registered

        # Get by name should return the latest
        retrieved = ModuleRegistry.get_module("duplicate_name")
        assert retrieved is TestModule2

    def test_get_modules_empty_registry(self):
        """Test get_modules when registry is empty."""
        modules = ModuleRegistry.get_modules()
        assert modules == []

    def test_modules_list_is_independent_copy(self):
        """Test that returned modules list is independent of internal storage."""

        class TestModule(ModuleBase):
            @classmethod
            def get_name(cls):
                return "independent_test"

            def register_tools(self, mcp):
                pass

        ModuleRegistry.register(TestModule)

        modules1 = ModuleRegistry.get_modules()
        modules2 = ModuleRegistry.get_modules()

        # Should be separate list objects
        assert modules1 is not modules2

        # But contain the same modules
        assert modules1 == modules2

    def test_module_registry_singleton_pattern(self):
        """Test that ModuleRegistry follows singleton pattern."""
        registry1 = ModuleRegistry()
        registry2 = ModuleRegistry()

        # Should be the same instance
        assert registry1 is registry2

    def test_module_registry_class_level_storage(self):
        """Test that ModuleRegistry uses class-level storage."""

        class TestModule(ModuleBase):
            @classmethod
            def get_name(cls):
                return "class_level_test"

            def register_tools(self, mcp):
                pass

        # Register via class method
        ModuleRegistry.register(TestModule)

        # Should be accessible via class method
        modules = ModuleRegistry.get_modules()
        assert TestModule in modules

        # Verify it's stored at class level
        assert hasattr(ModuleRegistry, "_modules")
        assert len(ModuleRegistry._modules) > 0
        assert "class_level_test" in ModuleRegistry._modules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

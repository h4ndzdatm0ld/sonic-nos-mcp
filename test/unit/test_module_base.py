"""Unit tests for module_base."""

import pytest
from unittest.mock import Mock

from sonic_nos_mcp.module_base import ModuleBase


class TestModuleBase:
    """Test ModuleBase abstract class."""

    def test_module_base_is_abstract(self):
        """Test that ModuleBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ModuleBase()

    def test_concrete_module_implementation(self):
        """Test concrete implementation of ModuleBase."""

        class ConcreteModule(ModuleBase):
            """Concrete implementation for testing."""

            def register_tools(self, mcp):
                """Test implementation of register_tools."""
                pass

        # Should be able to instantiate concrete implementation
        module = ConcreteModule()
        assert isinstance(module, ModuleBase)

        # Should have the register_tools method
        assert hasattr(module, "register_tools")

        # Should be able to call register_tools
        mock_mcp = Mock()
        module.register_tools(mock_mcp)  # Should not raise exception

    def test_register_tools_method_signature(self):
        """Test that register_tools method has correct signature."""

        class TestModule(ModuleBase):
            def register_tools(self, mcp):
                return "test_result"

        module = TestModule()
        mock_mcp = Mock()

        # Should accept mcp parameter and return value
        result = module.register_tools(mock_mcp)
        assert result == "test_result"

    def test_multiple_concrete_implementations(self):
        """Test multiple concrete implementations of ModuleBase."""

        class Module1(ModuleBase):
            def register_tools(self, mcp):
                return "module1"

        class Module2(ModuleBase):
            def register_tools(self, mcp):
                return "module2"

        module1 = Module1()
        module2 = Module2()

        mock_mcp = Mock()

        assert module1.register_tools(mock_mcp) == "module1"
        assert module2.register_tools(mock_mcp) == "module2"

        # Verify they are different instances
        assert module1 is not module2
        assert isinstance(module1, ModuleBase)
        assert isinstance(module2, ModuleBase)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

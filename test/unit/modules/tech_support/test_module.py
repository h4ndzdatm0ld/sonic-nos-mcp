"""Unit tests for tech_support module."""

import pytest
from unittest.mock import Mock, patch, mock_open

from sonic_nos_mcp.modules.tech_support.module import TechSupportModule


class TestTechSupportModule:
    """Test TechSupportModule functionality."""

    def test_tech_support_module_creation(self):
        """Test creating TechSupportModule instance."""
        module = TechSupportModule()
        assert isinstance(module, TechSupportModule)
        assert hasattr(module, "register_tools")

    @patch("sonic_nos_mcp.modules.tech_support.module.Path")
    @patch("builtins.open", new_callable=mock_open, read_data="title: Test Title\ncontent: Test Content")
    @patch("sonic_nos_mcp.modules.tech_support.module.yaml.safe_load")
    def test_register_tools_with_yaml_resource(self, mock_yaml_load, mock_file, mock_path):
        """Test register_tools method with successful YAML loading."""
        # Mock YAML data
        mock_yaml_data = {"title": "Test Tech Support Guide", "content": "Test content for tech support analysis"}
        mock_yaml_load.return_value = mock_yaml_data

        # Mock path exists
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        # Mock FastMCP
        mock_mcp = Mock()

        # Test the registration
        module = TechSupportModule()
        module.register_tools(mock_mcp)

        # Verify resource was registered
        mock_mcp.resource.assert_called()
        # Verify tools were registered
        assert mock_mcp.tool.call_count >= 3  # Should register 3 tools

    @patch("sonic_nos_mcp.modules.tech_support.module.Path")
    def test_register_tools_yaml_file_not_exists(self, mock_path):
        """Test register_tools when YAML file doesn't exist."""
        # Mock path doesn't exist
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        mock_mcp = Mock()

        module = TechSupportModule()
        module.register_tools(mock_mcp)

        # Should still register tools and resource (with fallback content)
        mock_mcp.resource.assert_called()
        assert mock_mcp.tool.call_count >= 3

    @patch("sonic_nos_mcp.modules.tech_support.module.Path")
    @patch("builtins.open", side_effect=IOError("File read error"))
    def test_register_tools_yaml_read_error(self, mock_file, mock_path):
        """Test register_tools when YAML file read fails."""
        # Mock path exists but read fails
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_mcp = Mock()

        module = TechSupportModule()
        module.register_tools(mock_mcp)

        # Should still register tools with fallback content
        mock_mcp.resource.assert_called()
        assert mock_mcp.tool.call_count >= 3

    def test_resource_loading_failure_handling(self):
        """Test that resource loading fails properly without fallback."""
        module = TechSupportModule()
        # The fallback content method has been removed - resource loading should fail cleanly
        assert not hasattr(module, "_get_fallback_content")

    @patch("sonic_nos_mcp.modules.tech_support.module.extract_tech_support")
    def test_extract_tech_support_file_tool_registration(self, mock_extract_function):
        """Test that extract_tech_support_file tool is registered correctly."""
        mock_mcp = Mock()
        mock_extract_function.return_value = Mock(
            extract_dir="/test/dir", success=True, error_message=None, files=["file1.txt"]
        )

        module = TechSupportModule()
        module.register_tools(mock_mcp)

        # Verify tool registration occurred (should be called at least 1 time for extract tool)
        tool_calls = mock_mcp.tool.call_args_list
        assert len(tool_calls) >= 1, f"Expected at least 1 tool registration, got {len(tool_calls)}"

        # Check that tool() decorator was called with description containing extract
        found_extract_tool = False
        for call in tool_calls:
            # Check both args and kwargs for description
            args, kwargs = call
            description = kwargs.get("description", "")
            if "extract" in description.lower() and "tech support" in description.lower():
                found_extract_tool = True
                break

        assert found_extract_tool, f"extract_tech_support_file tool should be registered. Tool calls: {tool_calls}"

    @patch("sonic_nos_mcp.modules.tech_support.module.list_tech_support_files")
    def test_list_tech_support_files_tool_registration(self, mock_list_function):
        """Test that list_tech_support_files_tool is registered correctly."""
        mock_mcp = Mock()
        mock_list_function.return_value = Mock(files=[], success=True, error_message=None)

        module = TechSupportModule()
        module.register_tools(mock_mcp)

        # Verify tool registration occurred
        assert mock_mcp.tool.call_count >= 3

    @patch("sonic_nos_mcp.modules.tech_support.module.get_tech_support_file_content")
    def test_get_tech_support_file_content_tool_registration(self, mock_content_function):
        """Test that get_tech_support_file_content_tool is registered correctly."""
        mock_mcp = Mock()
        mock_content_function.return_value = Mock(
            content="test content",
            matches=[],
            page=1,
            total_pages=1,
            file_path="/test/file.txt",
            success=True,
            error_message=None,
        )

        module = TechSupportModule()
        module.register_tools(mock_mcp)

        # Verify tool registration
        assert mock_mcp.tool.call_count >= 3

    def test_register_tools_with_exception_handling(self):
        """Test that register_tools handles exceptions gracefully."""
        mock_mcp = Mock()
        mock_mcp.tool.side_effect = Exception("Tool registration failed")

        module = TechSupportModule()

        # Should not raise exception
        try:
            module.register_tools(mock_mcp)
        except Exception as e:
            pytest.fail(f"register_tools should handle exceptions gracefully: {e}")

    def test_resource_registration(self):
        """Test that SONiC tech support guide resource is registered."""
        mock_mcp = Mock()

        module = TechSupportModule()
        module.register_tools(mock_mcp)

        # Verify resource was registered
        mock_mcp.resource.assert_called_once()

        # Verify resource URI and description
        resource_call = mock_mcp.resource.call_args
        resource_uri = resource_call[0][0]  # First positional argument

        assert resource_uri == "sonic://tech-support-guide"

        # Verify description contains expected keywords
        resource_kwargs = resource_call[1]  # Keyword arguments
        if "description" in resource_kwargs:
            description = resource_kwargs["description"]
            assert "SONiC" in description
            assert "tech support" in description.lower()


class TestTechSupportModuleIntegration:
    """Test tech support module integration."""

    def test_module_can_be_imported_and_used(self):
        """Test that module can be imported and used in real scenario."""
        # This test verifies the module works in practice
        module = TechSupportModule()

        # Should be able to register tools with mock MCP
        mock_mcp = Mock()
        module.register_tools(mock_mcp)

        # Verify registration occurred
        assert mock_mcp.resource.called
        assert mock_mcp.tool.called

    def test_module_self_registration(self):
        """Test that module can register itself with ModuleRegistry."""
        # Test that the module class can be registered (functionality test)
        from sonic_nos_mcp.module_registry import ModuleRegistry

        # Clear registry for clean test
        original_modules = ModuleRegistry._modules.copy()
        ModuleRegistry._modules = {}

        try:
            # Register the module class manually to test the mechanism
            ModuleRegistry.register(TechSupportModule)

            # Verify it was registered
            modules = ModuleRegistry.get_modules()
            assert len(modules) == 1
            assert TechSupportModule in modules

        finally:
            # Restore original registry state
            ModuleRegistry._modules = original_modules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

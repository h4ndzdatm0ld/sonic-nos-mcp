"""Unit tests for server."""

import pytest
from unittest.mock import Mock, patch

from sonic_nos_mcp.server import main, SonicNosMcpServer
from sonic_nos_mcp.module_registry import ModuleRegistry
from sonic_nos_mcp.module_base import ModuleBase


class TestSonicNosMcpServer:
    """Test SonicNosMcpServer class functionality."""

    def setup_method(self):
        """Setup method to clear registry."""
        ModuleRegistry._modules = {}

    def teardown_method(self):
        """Teardown to clean registry."""
        ModuleRegistry._modules = {}

    @patch("sonic_nos_mcp.server.ModuleRegistry.get_modules")
    @patch("sonic_nos_mcp.server.FastMCP")
    def test_server_initialization(self, mock_fastmcp, mock_get_modules):
        """Test SonicNosMcpServer initialization."""
        mock_get_modules.return_value = []
        mock_mcp_instance = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        server = SonicNosMcpServer()

        # Verify FastMCP was created
        mock_fastmcp.assert_called_once_with("sonic-nos-mcp-server", log_level="ERROR")
        assert server.mcp is mock_mcp_instance

    @patch("sonic_nos_mcp.server.ModuleRegistry.get_modules")
    @patch("sonic_nos_mcp.server.FastMCP")
    def test_server_with_modules(self, mock_fastmcp, mock_get_modules):
        """Test server initialization with registered modules."""

        # Create mock module
        class TestModule(ModuleBase):
            @classmethod
            def get_name(cls):
                return "test_module"

            def register_tools(self, mcp):
                pass

        mock_get_modules.return_value = [TestModule]
        mock_mcp_instance = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        SonicNosMcpServer()

        # Verify module loading was attempted
        mock_get_modules.assert_called_once()

    @patch("sonic_nos_mcp.server.ModuleRegistry.get_modules")
    @patch("sonic_nos_mcp.server.FastMCP")
    def test_server_module_registration_error(self, mock_fastmcp, mock_get_modules):
        """Test server handles module registration errors gracefully."""

        class ProblematicModule(ModuleBase):
            @classmethod
            def get_name(cls):
                return "problematic"

            def register_tools(self, mcp):
                raise Exception("Registration failed")

        mock_get_modules.return_value = [ProblematicModule]
        mock_mcp_instance = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Should not raise exception
        server = SonicNosMcpServer()
        assert server is not None

    @patch("sonic_nos_mcp.server.FastMCP")
    def test_server_run_method(self, mock_fastmcp):
        """Test server run method."""
        mock_mcp_instance = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        server = SonicNosMcpServer()

        # Test run with default transport
        server.run()
        mock_mcp_instance.run.assert_called_with(transport="stdio")

        # Test run with http transport
        server.run(transport="http")
        mock_mcp_instance.run.assert_called_with(transport="http")


class TestMainFunction:
    """Test main function."""

    @patch("sonic_nos_mcp.server.SonicNosMcpServer")
    @patch("sonic_nos_mcp.server.argparse.ArgumentParser.parse_args")
    def test_main_function_basic(self, mock_parse_args, mock_server_class):
        """Test main function execution."""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.transport = "stdio"
        mock_args.log_level = "ERROR"
        mock_parse_args.return_value = mock_args

        # Mock server
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        # Call main function
        main()

        # Verify server creation and run
        mock_server_class.assert_called_once()
        mock_server.run.assert_called_once_with(transport="stdio")

    @patch("sonic_nos_mcp.server.SonicNosMcpServer")
    @patch("sonic_nos_mcp.server.argparse.ArgumentParser.parse_args")
    def test_main_function_with_http_transport(self, mock_parse_args, mock_server_class):
        """Test main function with HTTP transport."""
        mock_args = Mock()
        mock_args.transport = "http"
        mock_args.log_level = "DEBUG"
        mock_parse_args.return_value = mock_args

        mock_server = Mock()
        mock_server_class.return_value = mock_server

        main()

        mock_server.run.assert_called_once_with(transport="http")

    @patch("sonic_nos_mcp.server.SonicNosMcpServer")
    @patch("sonic_nos_mcp.server.argparse.ArgumentParser.parse_args")
    def test_main_function_keyboard_interrupt(self, mock_parse_args, mock_server_class):
        """Test main function handles KeyboardInterrupt."""
        mock_args = Mock()
        mock_args.transport = "stdio"
        mock_args.log_level = "ERROR"
        mock_parse_args.return_value = mock_args

        mock_server = Mock()
        mock_server.run.side_effect = KeyboardInterrupt()
        mock_server_class.return_value = mock_server

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0  # Should exit with code 0

    @patch("sonic_nos_mcp.server.SonicNosMcpServer")
    @patch("sonic_nos_mcp.server.argparse.ArgumentParser.parse_args")
    def test_main_function_server_exception(self, mock_parse_args, mock_server_class):
        """Test main function handles server exceptions."""
        mock_args = Mock()
        mock_args.transport = "stdio"
        mock_args.log_level = "ERROR"
        mock_parse_args.return_value = mock_args

        mock_server_class.side_effect = Exception("Server creation failed")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1  # Should exit with code 1 on error

    @patch("sonic_nos_mcp.server.logging.basicConfig")
    @patch("sonic_nos_mcp.server.argparse.ArgumentParser.parse_args")
    def test_main_function_logging_setup(self, mock_parse_args, mock_basic_config):
        """Test main function sets up logging."""
        mock_args = Mock()
        mock_args.transport = "stdio"
        mock_args.log_level = "INFO"
        mock_parse_args.return_value = mock_args

        with patch("sonic_nos_mcp.server.SonicNosMcpServer") as mock_server:
            mock_server.return_value.run.side_effect = KeyboardInterrupt()

            try:
                main()
            except SystemExit:
                pass

        # Verify logging was configured
        mock_basic_config.assert_called_once()


class TestServerIntegration:
    """Test server integration scenarios."""

    def setup_method(self):
        """Setup method."""
        ModuleRegistry._modules = {}

    def teardown_method(self):
        """Cleanup."""
        ModuleRegistry._modules = {}

    @patch("sonic_nos_mcp.server.FastMCP")
    def test_server_with_tech_support_module(self, mock_fastmcp):
        """Test server integration with tech support module."""
        # Import and register the actual tech support module
        from sonic_nos_mcp.modules.tech_support.module import TechSupportModule

        # Register the module (this happens during import normally)
        ModuleRegistry.register(TechSupportModule)

        mock_mcp_instance = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Create server
        server = SonicNosMcpServer()

        # Verify server was created successfully
        assert server is not None

        # Verify module was registered
        modules = ModuleRegistry.get_modules()
        assert len(modules) > 0
        assert TechSupportModule in modules

    @patch("sonic_nos_mcp.server.FastMCP")
    def test_end_to_end_server_startup(self, mock_fastmcp):
        """Test end-to-end server startup process."""
        # This simulates what happens during normal startup

        # Step 1: Module imports and registration (simulated)
        class MockTechSupportModule(ModuleBase):
            @classmethod
            def get_name(cls):
                return "tech_support"

            def register_tools(self, mcp):
                # Mock tool registration
                mcp.tool_registered = True

        ModuleRegistry.register(MockTechSupportModule)

        mock_mcp_instance = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Step 2: Server creation
        server = SonicNosMcpServer()

        # Step 3: Verify everything is set up
        assert server is not None
        modules = ModuleRegistry.get_modules()
        assert len(modules) == 1
        assert modules[0] is MockTechSupportModule


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Tech Context - SONiC NOS MCP Server

## Technologies Used

### Core Technologies
- **Python 3.11+**: Modern Python with type hints and async support
- **UV**: Fast Python package installer and resolver for dependency management
- **MCP (Model Context Protocol)**: Claude's protocol for connecting external tools and data sources

### Dependencies
See `pyproject.toml` for the complete list of dependencies and their versions. Key packages include:
- **mcp[cli]**: MCP server framework
- **pydantic**: Data validation using Python type annotations
- **pyyaml**: YAML parsing for embedded resources

Development dependencies are managed via hatch environments (testing, linting, formatting).

## Development Setup

### Environment Management
- **UV Virtual Environment**: `.venv/` directory contains isolated Python environment
- **Python Version**: 3.11+ required, 3.12 configured in hatch env
- **Dependency Locking**: `uv.lock` ensures reproducible builds
- **Build System**: Hatchling for modern Python packaging

### Package Configuration
- **Entry Point**: `sonic-nos-mcp` command points to `sonic_nos_mcp.server:main`
- **Import Style**: Absolute imports throughout codebase
- **Module Discovery**: Automatic registration through import side effects

## Technical Constraints

### MCP Protocol Requirements
- **Stdio Transport**: Primary communication method with MCP clients
- **JSON-RPC**: Underlying protocol for tool calls and responses
- **Type Safety**: All tool parameters must be properly typed
- **Error Handling**: Graceful error responses in MCP format

### File Processing Constraints
- **Memory Management**: Large files require chunked processing
- **Temporary Files**: Secure temporary directory handling
- **Archive Formats**: Support for tar.gz, zip, and other common formats
- **Compression**: Automatic decompression for .gz, .bz2, .xz files

### Performance Considerations
- **Lazy Loading**: Modules loaded only when needed
- **Streaming**: Large file content delivered in pages
- **Caching**: Temporary extraction directories for repeated access
- **Resource Cleanup**: Automatic cleanup of temporary resources

## Tool Usage Patterns

### UV Commands
```bash
uv sync                    # Install dependencies
uv run sonic-nos-mcp       # Run MCP server
uv run hatch run test:pytest test/    # Run tests (proper environment)
uv run mypy src/           # Type checking
uv run ruff check .        # Linting (entire project)
uv run black .             # Code formatting
```

### Development Workflow
1. **Environment Setup**: `uv sync` to install dependencies
2. **Code Changes**: Edit source files with proper typing
3. **Validation**: `uv run ruff check` and `uv run mypy`
4. **Testing**: `uv run pytest` for functionality verification
5. **Server Testing**: Manual MCP client connection tests

### MCP Client Integration
- **VS Code**: Through MCP extension configuration
- **CLI Tools**: Direct stdio communication
- **Testing**: MCP inspector for development/debugging

## Archive Processing Technology

### Supported Formats
- **tar.gz, tgz**: Gzipped tar archives (most common for SONiC)
- **zip**: Standard ZIP archives
- **tar.bz2, tar.xz**: Alternative compression formats
- **tar**: Uncompressed tar archives

### Extraction Strategy
- **Python tarfile**: Built-in tar handling
- **Python zipfile**: Built-in ZIP handling
- **Temporary Directories**: System temp directory or user-specified
- **Path Validation**: Secure extraction preventing directory traversal

## SONiC Integration Points

### File Structure Knowledge
- **Database Files**: JSON dumps from Redis databases
- **Log Files**: Compressed system and application logs
- **Configuration Files**: System configuration snapshots
- **Proc Files**: Linux kernel interface dumps

### Domain-Specific Processing
- **JSON Parsing**: Efficient handling of large database dumps
- **Log Analysis**: Regex pattern matching in compressed logs
- **File Filtering**: SONiC-aware file importance ranking
- **Content Chunking**: Smart pagination for different file types

## Extension Architecture

### Future Module Support
- **YANG Models**: SONiC YANG schema validation and processing
- **Configuration Management**: Config generation and validation
- **Real-time Monitoring**: Live device state collection
- **Automation Tools**: Network configuration automation

### Plugin Interface
- **ModuleBase**: Abstract interface for all modules
- **Tool Registration**: Decorator-based tool registration
- **Resource System**: Static content and documentation
- **Configuration**: Module-specific settings and parameters

# sonic-nos-mcp
SONiC Network Operating System MCP Server. Collection of tools for SONiC.

## Overview

The SONiC NOS MCP Server provides tools for analyzing SONiC network device diagnostic data through the Model Context Protocol (MCP). It offers modular capabilities for extracting, listing, and inspecting SONiC tech support files, making network troubleshooting more efficient and accessible to humans and LLM based troubleshooting workflows, Agents, etc.

## MCP Configuration

### Prerequisites

#### For UV/Direct Execution (Development)
- Python 3.11+
- [UV package manager](https://docs.astral.sh/uv/) installed
- Git clone of this repository

#### For Docker Execution (Production)
- Docker installed and running
- Internet connection to pull the container image

### Configuration Examples

Add one of the following configurations to your MCP client settings:

#### Option 1: UV/Direct Execution (Recommended for Development)

```json
{
  "mcpServers": {
    "sonic-nos": {
      "command": "uv",
      "args": ["run", "sonic-nos-mcp"],
      "cwd": "/path/to/sonic-nos-mcp"
    }
  }
}
```

**Setup Instructions:**
1. Clone this repository: `git clone https://github.com/h4ndzdatm0ld/sonic-nos-mcp.git`
2. Navigate to the directory: `cd sonic-nos-mcp`
3. Install dependencies: `uv sync`
4. Update the `cwd` path in your MCP configuration to point to your cloned directory

#### Option 2: Docker Execution (Recommended for Production)

**Basic Docker Configuration:**
```json
{
  "mcpServers": {
    "sonic-nos": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "h4ndzdatm0ld/sonic-nos-mcp:latest"
      ]
    }
  }
}
```

**Docker Configuration with File Access and Auto-Approve:**
```json
{
  "mcpServers": {
    "sonic-nos": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--mount",
        "type=bind,src=/Users/htinoco/Desktop,dst=/Users/htinoco/Desktop",
        "h4ndzdatm0ld/sonic-nos-mcp:latest"
      ],
      "autoApprove": [
        "extract_tech_support_file",
        "read_tech_support_file"
      ]
    }
  }
}
```

**Setup Instructions:**
1. Pull the Docker image: `docker pull h4ndzdatm0ld/sonic-nos-mcp:latest`
2. Update the bind mount source path (`src=`) to match your local directory containing tech support files
3. The `autoApprove` setting automatically approves safe read-only operations

### Supported MCP Clients

This server works with any MCP-compatible client, including:
- **Claude Desktop**: Add configuration to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
- **VS Code with MCP Extension**: Add to your workspace or user settings
- **Custom MCP Clients**: Use the stdio transport protocol

### Available Tools

- `extract_tech_support_file`: Extract and process SONiC tech support archives
- `list_tech_support_files_tool`: List files within extracted archives with filtering
- `get_tech_support_file_content_tool`: Read and search file contents with regex patterns

### Troubleshooting

**UV Method Issues:**
- Ensure UV is installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Verify Python 3.11+: `python --version`
- Check dependencies: `uv sync` in the project directory

**Docker Method Issues:**
- Ensure Docker is running: `docker --version`
- Pull latest image: `docker pull h4ndzdatm0ld/sonic-nos-mcp:latest`
- Check container logs: `docker logs <container-id>`

**MCP Client Issues:**
- Verify JSON configuration syntax
- Check file paths are absolute and accessible
- Restart your MCP client after configuration changes

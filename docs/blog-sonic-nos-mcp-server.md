---
title: "Simplifying SONiC Network Troubleshooting with AI-Powered MCP Server"
date: 2025-11-09
author: Hugo Tinoco
tags: [SONiC, MCP, AI, Network Troubleshooting, DevOps, Automation]
description: "Discover how the SONiC NOS MCP Server brings AI-powered network troubleshooting to SONiC devices through the Model Context Protocol, enabling intelligent root cause analysis and streamlined diagnostic workflows."
---

# Simplifying SONiC Network Troubleshooting with AI-Powered MCP Server

Network troubleshooting has long been a time-consuming and expertise-intensive process. When network issues arise in SONiC (Software for Open Networking in the Cloud) environments, engineers often spend hours manually sifting through tech support files, correlating logs, and analyzing system states. The SONiC NOS MCP Server changes this paradigm by bringing AI-powered analysis capabilities directly to network diagnostic workflows through the Model Context Protocol (MCP).

## The Challenge: Manual SONiC Diagnostics

Network engineers working with SONiC devices face several challenges when troubleshooting network issues:

- **Information Overload**: Tech support archives contain hundreds of files with varying importance and relevance
- **Manual Analysis**: Engineers manually extract and navigate through complex directory structures
- **File Format Complexity**: Multiple file formats including JSON databases, compressed logs, and system dumps
- **Knowledge Barriers**: Deep understanding of SONiC file structure and contents is required
- **Time-Intensive Process**: Hours spent correlating data across multiple files and log sources

Traditional troubleshooting workflows require network engineers to:
1. Download tech support files from affected devices
2. Manually extract compressed archives
3. Navigate complex directory structures
4. Identify relevant configuration and log files
5. Correlate information across multiple sources
6. Apply domain expertise to determine root causes

This process is not only time-consuming but also prone to human error and inconsistent results across different engineers.

## The Solution: AI-Powered MCP Integration

The SONiC NOS MCP Server provides a revolutionary approach to network diagnostics by integrating AI capabilities through the Model Context Protocol. MCP is an open protocol that enables seamless communication between AI applications and data sources, making it possible for AI assistants like Claude, ChatGPT, and other LLMs to intelligently analyze SONiC diagnostic data.

### What is the Model Context Protocol?

The Model Context Protocol (MCP) is an open standard that allows AI applications to securely connect to data sources and tools. Think of it as a universal adapter that enables AI assistants to interact with specialized systems and data repositories. For SONiC networks, this means AI can directly access and analyze tech support files, configuration databases, and system logs without requiring manual data preparation.

### Key Features

The SONiC NOS MCP Server provides three core tools designed for comprehensive diagnostic analysis:

#### 1. Tech Support File Extraction
- Automatically handles `.tar.gz`, `.zip`, and `.tgz` archives
- Recursively extracts nested archives
- Returns complete file inventory with metadata
- Cleans up empty files for efficient analysis
- Smart extraction to temporary directories

#### 2. Intelligent File Listing
- Optional glob pattern filtering (`*.json`, `dump/*`)
- Directory structure navigation
- File categorization by type and purpose
- Quick identification of relevant diagnostic files

#### 3. Content Analysis and Inspection
- Regex-based pattern matching for targeted analysis
- Automatic chunking for large files
- Read any file with automatic decompression
- Search content across multiple files
- Extract relevant sections efficiently

### Modular Architecture

The MCP server is built with extensibility in mind:

```
sonic-nos-mcp/
├── src/sonic_nos_mcp/
│   ├── module_base.py          # Extensible module system
│   ├── module_registry.py      # Auto-discovery
│   └── modules/
│       └── tech_support/       # First module
│           ├── tools/          # Extract, List, Read
│           ├── models/         # Pydantic schemas
│           └── resources/      # SONiC knowledge base
```

This modular design makes it easy to add new SONiC analysis capabilities as the project evolves.

## How It Works: AI-Powered Root Cause Analysis

The SONiC NOS MCP Server enables sophisticated AI-powered workflows for network troubleshooting. Here's how a typical root cause analysis workflow operates:

### 5-Step RCA Pipeline

Using AI agent frameworks like Strands with Claude Sonnet 4.5, the analysis follows a systematic approach:

1. **Problem Clarification** - AI focuses the analysis scope based on the problem description
2. **Tech Support Extraction** - Smart file discovery and extraction
3. **Targeted Data Collection** - Evidence gathering from relevant files
4. **Evidence Correlation** - Cross-file analysis to identify patterns
5. **Root Cause Determination** - Definitive diagnosis with supporting evidence

### Real-World Example: BGP Authentication Failure

Let's walk through a real troubleshooting scenario:

**Problem Statement**: "BGP neighbor 10.255.0.2 keeps flapping and won't establish session"

**Analysis Process**:
```bash
uv run python examples/invokeWorkflow.py \
  --prompt "BGP neighbor 10.255.0.2 keeps flapping and won't establish session" \
  --tech-support-file test/data/techsupport/techsupport_bgp_md5.tar.gz \
  --verbose
```

**What the AI Does**:
1. Extracts the tech support archive
2. Identifies relevant BGP configuration files (CONFIG_DB.json)
3. Examines FRR daemon configuration and logs
4. Checks neighbor status and authentication settings
5. Correlates configuration mismatches
6. Identifies MD5 authentication password mismatch ("wrongpw")
7. Generates comprehensive RCA report with actionable recommendations

**Results**: The AI agent achieved a perfect 5/5 score from LLM Judge evaluation, correctly identifying the root cause with expert-level diagnosis, all in under 5 minutes compared to potentially hours of manual analysis.

## Getting Started

### Prerequisites

Choose your preferred deployment method:

#### Option 1: UV/Direct Execution (Development)
- Python 3.11 or higher
- UV package manager installed
- Git clone of the repository

#### Option 2: Docker Execution (Production)
- Docker installed and running
- Internet connection to pull the container image

### Quick Start with UV

```bash
# Clone the repository
git clone https://github.com/h4ndzdatm0ld/sonic-nos-mcp.git
cd sonic-nos-mcp

# Install dependencies
uv sync

# Configure your MCP client (Claude Desktop, VS Code, etc.)
```

### MCP Client Configuration

Add to your MCP client settings (e.g., Claude Desktop config at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

### Quick Start with Docker

```bash
# Pull the Docker image
docker pull ghcr.io/h4ndzdatm0ld/sonic-nos-mcp:latest

# Configure with file access
```

Docker configuration with file access:
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
        "type=bind,src=/path/to/your/techsupport/files,dst=/path/to/your/techsupport/files",
        "ghcr.io/h4ndzdatm0ld/sonic-nos-mcp:latest"
      ],
      "autoApprove": [
        "extract_tech_support_file",
        "read_tech_support_file"
      ]
    }
  }
}
```

The `autoApprove` setting automatically approves safe read-only operations, streamlining your workflow.

## Use Cases and Benefits

### For Network Engineers
- **Reduce diagnostic time** from hours to minutes
- **Access embedded expertise** through AI-powered analysis
- **Consistent methodology** across teams and incidents
- **Natural language queries** instead of manual log parsing
- **Automated correlation** of events across multiple sources

### For Support Teams
- **Streamlined issue resolution** with AI-assisted analysis
- **Automated initial assessment** of customer issues
- **Clear documentation** of investigation steps
- **Faster time-to-resolution** for customer incidents
- **Knowledge transfer** through embedded best practices

### For DevOps Teams
- **Integration with existing workflows** through MCP protocol
- **Scriptable diagnostic procedures** for automation
- **Standardized troubleshooting processes** across environments
- **CI/CD pipeline integration** for proactive monitoring
- **Automated report generation** for incident tracking

## Advanced Capabilities

### Multiple Troubleshooting Scenarios

The SONiC NOS MCP Server handles various diagnostic scenarios:

**Memory/OOM Analysis**:
```bash
uv run python examples/invokeWorkflow.py \
  --prompt "System experiencing out of memory conditions" \
  --tech-support-file test/data/techsupport/techsupport_oom.tar.gz
```

**System Crash Investigation**:
```bash
uv run python examples/invokeWorkflow.py \
  --prompt "syncd process keeps crashing" \
  --tech-support-file test/data/techsupport/techsupport_syncd_crash.tar.gz
```

### AI Agent Workflows

The project includes sophisticated multi-agent workflows using the Strands Agent Framework:

- **Single Agent Mode**: Excels with clear problem statements on both simple and complex scenarios
- **Multi-Agent Workflows**: Better deep dive analysis through task-specific agent specialization
- **Interactive Analysis**: Integration with Cline provides real-time guidance during analysis

### Production-Grade Quality

The MCP server is built with enterprise requirements in mind:

**Security & Reliability**:
- No external API calls - all processing is local
- Comprehensive logging with full audit trail
- Docker containers for production deployment
- Security scanning with Bandit and Safety

**Quality Gates**:
- Ruff formatting and linting with auto-fix
- MyPy static type checking (100% coverage)
- 90%+ test coverage requirement
- Automated vulnerability detection

**CI/CD Pipeline**:
- GitHub Actions workflows for all branches
- Multi-version Python testing (3.11, 3.12, 3.13)
- Container quality validation
- Automated publishing to GitHub Container Registry

## Testing and Validation

The project includes comprehensive test scenarios with realistic data:

| Scenario | Issue Type | Key Problems |
|----------|-----------|--------------|
| BGP MD5 Authentication | Routing Protocol | MD5 password mismatch, neighbor flapping |
| Memory Exhaustion | System Resources | OOM conditions, container restarts |
| syncd Crash | Process Management | Daemon crashes, hardware interface issues |

### Evaluation Framework

An LLM Judge evaluation framework validates AI agent performance:
- Average score: 5.0/5 (9 runs)
- Success rate: 77.8%
- Average response time: 254.6 seconds

## Containerlab Integration

For testing and development, pre-built SONiC images are available:

**Available Images**:
- SONiC 202411
- SONiC 202505

**Example Topology**:
```yaml
name: sonic-duo-202411
prefix: clab

topology:
  nodes:
    sonic1:
      kind: sonic-vm
      image: h4ndzdatm0ld/sonic-vm:202411
      startup-config: ./configs/sonic1_config_db.json
    sonic2:
      kind: sonic-vm
      image: h4ndzdatm0ld/sonic-vm:202411
      startup-config: ./configs/sonic2_config_db.json
  links:
    - endpoints: ["sonic1:eth1", "sonic2:eth1"]
    - endpoints: ["sonic1:eth2", "sonic2:eth2"]
mgmt:
  network: sonic-mgmt
  ipv4_subnet: 172.20.20.0/24
```

## Supported MCP Clients

The server works with any MCP-compatible client:
- **Claude Desktop**: AI-powered analysis through Claude
- **VS Code with MCP Extension**: IDE integration
- **Custom MCP Clients**: Use the stdio transport protocol
- **AI Agent Frameworks**: Strands, LangChain, and others

## Future Roadmap

The SONiC NOS MCP Server is designed for extensibility with future enhancements planned:

- Additional SONiC analysis modules
- Real-time device interaction capabilities
- YANG model processing integration
- Advanced pattern matching and anomaly detection
- Integration with external SONiC tools and platforms
- Community-contributed analysis modules

## Community and Contributions

The SONiC NOS MCP Server is an open-source project developed during the SONiC Hackathon 2025. We welcome contributions from the community!

**Repository**: [https://github.com/h4ndzdatm0ld/sonic-nos-mcp](https://github.com/h4ndzdatm0ld/sonic-nos-mcp)

**Related Projects**:
- ContainerLabs: [https://github.com/h4ndzdatm0ld/clab-sonic](https://github.com/h4ndzdatm0ld/clab-sonic)
- SONiC Images: [https://hub.docker.com/repository/docker/h4ndzdatm0ld/sonic-vs/general](https://hub.docker.com/repository/docker/h4ndzdatm0ld/sonic-vs/general)

## Conclusion

The SONiC NOS MCP Server represents a paradigm shift in network troubleshooting, bringing AI-powered analysis capabilities to SONiC environments. By leveraging the Model Context Protocol, network engineers can now diagnose complex issues in minutes rather than hours, with consistent, expert-level analysis.

Whether you're a network engineer troubleshooting production issues, a support team member handling customer incidents, or a DevOps engineer building automation workflows, the SONiC NOS MCP Server provides the tools and intelligence needed to streamline your diagnostic processes.

Get started today and experience the future of AI-powered network troubleshooting!

## Resources

- **Documentation**: [README.md](https://github.com/h4ndzdatm0ld/sonic-nos-mcp/blob/main/README.md)
- **Examples**: [examples/](https://github.com/h4ndzdatm0ld/sonic-nos-mcp/tree/main/examples)
- **Docker Images**: [ghcr.io/h4ndzdatm0ld/sonic-nos-mcp](https://github.com/h4ndzdatm0ld/sonic-nos-mcp/pkgs/container/sonic-nos-mcp)
- **Author**: Hugo Tinoco - [LinkedIn](https://www.linkedin.com/in/hugo-tinoco)

---

*This blog post showcases the SONiC NOS MCP Server developed for the SONiC Hackathon 2025, demonstrating how MCP servers can provide intelligent diagnostic analysis for network device troubleshooting.*

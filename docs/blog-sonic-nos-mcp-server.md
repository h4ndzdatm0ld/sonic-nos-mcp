# Simplifying SONiC Network Troubleshooting with AI-Powered Analysis

**By Hugo Tinoco, Amazon**  
*January 2025*

---

## Introduction

Network troubleshooting has traditionally been a time-intensive, manual process requiring engineers to sift through thousands of log lines, correlate data across multiple files, and rely on deep tribal knowledge of system internals. With SONiC (Software for Open Networking in the Cloud) deployments growing rapidly, the need for intelligent, automated diagnostics has never been greater.

Enter the **SONiC NOS MCP Server** – an open-source solution that brings AI-powered network analysis to SONiC tech support dumps through the Model Context Protocol (MCP). This project transforms how network engineers and AI agents interact with SONiC diagnostic data, enabling natural language queries and automated root cause analysis.

## The Challenge: Manual Tech Support Analysis

When a SONiC device experiences issues, operators typically collect a tech support dump – a compressed archive containing configuration files, logs, system state, and diagnostic output. Analyzing these files manually presents several challenges:

- **Volume**: Tech support archives can contain hundreds of files and millions of log lines
- **Complexity**: Understanding requires knowledge of SONiC architecture, protocols, and subsystems
- **Time**: Manual correlation across logs, configs, and state files is slow and error-prone
- **Consistency**: Analysis quality varies based on engineer experience and fatigue

Traditional troubleshooting often involves:
1. Extracting the archive manually
2. Searching through directories to find relevant files
3. Using grep, awk, and other CLI tools to filter logs
4. Mentally correlating information across multiple sources
5. Consulting documentation or colleagues for obscure issues

This process can take hours or even days for complex problems, delaying resolution and impacting network availability.

## The Solution: AI-Powered MCP Server

The SONiC NOS MCP Server bridges the gap between human expertise and AI capabilities by providing a standardized interface for SONiC diagnostic analysis. Built on the [Model Context Protocol](https://modelcontextprotocol.io), it enables AI agents and assistants like Claude, ChatGPT, and custom LLM-based tools to intelligently analyze SONiC tech support files.

### What is MCP?

The Model Context Protocol is an open standard that enables AI models to securely interact with external data sources and tools. Think of it as an API that lets AI assistants "see" and "interact" with your data in a controlled, auditable way. MCP servers expose **tools** (callable functions) and **resources** (contextual knowledge) that AI models can use to accomplish tasks.

### Key Features

The SONiC NOS MCP Server provides three core tools designed for diagnostic workflows:

**1. Tech Support Extraction (`extract_tech_support_file`)**
- Handles `.tar.gz`, `.zip`, and `.tgz` archives automatically
- Recursively extracts nested archives (common in SONiC dumps)
- Returns complete file inventory with metadata
- Cleans up empty or corrupted files

**2. Smart File Navigation (`list_tech_support_files_tool`)**
- Glob pattern filtering (e.g., `*.json`, `bgp/*.log`)
- Directory structure exploration
- Selective file discovery based on analysis needs

**3. Intelligent File Reading (`read_tech_support_file`)**
- Regex pattern matching for targeted content extraction
- Automatic chunking for large files (prevents context overload)
- Multi-file correlation support
- Handles various file encodings

### Architecture: Built for Extensibility

The server uses a modular architecture that makes adding new capabilities straightforward:

```
sonic-nos-mcp/
├── src/sonic_nos_mcp/
│   ├── module_base.py          # Extensible module framework
│   ├── module_registry.py      # Auto-discovery system
│   └── modules/
│       └── tech_support/       # Tech support analysis module
│           ├── tools/          # MCP tool implementations
│           ├── models/         # Pydantic data schemas
│           └── resources/      # SONiC knowledge base
```

This design allows the community to contribute new modules for specific SONiC subsystems (BGP, VXLAN, QoS, etc.) or analysis types (performance trending, config validation, compliance checking).

## How It Works: AI Agent Workflows

The real power of the MCP server emerges when combined with AI agent frameworks. Here's how a typical root cause analysis workflow operates:

### 5-Step RCA Pipeline

**1. Problem Clarification**
```
User: "BGP neighbor 10.255.0.2 won't establish session"
Agent: Identifies this as a BGP peering issue, plans investigation strategy
```

**2. Tech Support Extraction**
```python
# Agent calls MCP tool
extract_tech_support_file(file_path="/path/to/techsupport.tar.gz")
# Returns inventory of 347 files extracted
```

**3. Targeted Data Collection**
```python
# Agent identifies relevant files
list_tech_support_files_tool(pattern="*bgp*")
# Finds: CONFIG_DB.json, frr.conf, bgpd.log, show_bgp_summary.txt

# Agent reads specific configurations
read_tech_support_file(
    file_path="CONFIG_DB.json",
    pattern="BGP_NEIGHBOR.*10.255.0.2"
)
```

**4. Evidence Correlation**
```
Agent analyzes:
- BGP neighbor configuration (MD5 password: "wrongpw")
- FRR daemon configuration
- BGP session logs (authentication failures)
- Interface status (Layer 2 connectivity: OK)
```

**5. Root Cause Determination**
```
Agent concludes:
ROOT CAUSE: MD5 authentication password mismatch
- Neighbor configured with password "wrongpw"
- Remote side using different password
- TCP connection established but BGP session fails at auth

EVIDENCE:
- CONFIG_DB.json: "BGP_NEIGHBOR|10.255.0.2|password": "wrongpw"
- bgpd.log: "[ERROR] MD5 authentication failed for peer 10.255.0.2"

RESOLUTION:
1. Verify correct shared secret with peer administrator
2. Update BGP neighbor configuration
3. Monitor session establishment
```

### Real-World Performance

In testing with realistic tech support scenarios:
- **Average response time**: 254.6 seconds
- **Accuracy rate**: 77.8% successful diagnosis (9 test runs)
- **LLM Judge evaluation**: 5.0/5.0 average score
- **Scenarios tested**: BGP auth failures, syncd crashes, OOM conditions

The agent-based approach excels when given specific problem statements and struggles with vague prompts – similar to human experts.

## Use Cases

### Network Operations Center (NOC)
- **First-level triage**: AI agents pre-analyze tickets before human escalation
- **24/7 availability**: Instant analysis regardless of engineer availability
- **Consistent quality**: Same analysis depth every time
- **Knowledge retention**: No expertise lost to employee turnover

### DevOps/SRE Teams
- **CI/CD integration**: Automated testing of config changes against known failure patterns
- **Post-mortem analysis**: Rapid root cause identification after incidents
- **Compliance validation**: Automatic checking of configs against security policies

### Network Engineers
- **Interactive troubleshooting**: Natural language queries during active incidents
- **Training tool**: New engineers learn by observing AI analysis explanations
- **Documentation assistant**: Auto-generate RCA reports from tech support files

### Example CLI Usage

```bash
# BGP routing issue analysis
uv run python examples/invokeWorkflow.py \
  --prompt "BGP neighbor 10.255.0.2 keeps flapping" \
  --tech-support-file test/data/techsupport/techsupport_bgp_md5.tar.gz \
  --verbose

# Memory/OOM investigation
uv run python examples/invokeWorkflow.py \
  --prompt "System experiencing out of memory conditions" \
  --tech-support-file test/data/techsupport/techsupport_oom.tar.gz

# Container crash analysis
uv run python examples/invokeWorkflow.py \
  --prompt "syncd process keeps crashing" \
  --tech-support-file test/data/techsupport/techsupport_syncd_crash.tar.gz
```

## Getting Started

### Prerequisites
- Python 3.11 or higher
- UV package manager (recommended) or Docker
- SONiC tech support files (sample files included)

### Installation Options

#### Option 1: UV Development Setup (Recommended)
```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/h4ndzdatm0ld/sonic-nos-mcp.git
cd sonic-nos-mcp
uv sync
```

#### Option 2: Docker Production Deployment
```bash
# Pull the latest image
docker pull ghcr.io/h4ndzdatm0ld/sonic-nos-mcp:latest

# Run with file access
docker run -i --rm \
  --mount type=bind,src=/path/to/techsupport/files,dst=/data \
  ghcr.io/h4ndzdatm0ld/sonic-nos-mcp:latest
```

### MCP Client Configuration

Add to your Claude Desktop, VS Code MCP extension, or custom MCP client:

**UV Method:**
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

**Docker Method:**
```json
{
  "mcpServers": {
    "sonic-nos": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--mount", "type=bind,src=/Users/yourname/Desktop,dst=/Users/yourname/Desktop",
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

### Running Your First Analysis

1. **Prepare a tech support file** (or use included samples):
   ```bash
   # On SONiC device
   admin@sonic:~$ show techsupport
   # Generates /var/dump/sonic_dump_*.tar.gz
   ```

2. **Copy to your workstation**:
   ```bash
   scp admin@sonic:/var/dump/sonic_dump_*.tar.gz ./techsupport.tar.gz
   ```

3. **Run the analysis workflow**:
   ```bash
   cd sonic-nos-mcp
   uv run python examples/invokeWorkflow.py \
     --prompt "Describe your problem here" \
     --tech-support-file ./techsupport.tar.gz \
     --verbose
   ```

4. **Review the output**:
   - Console displays real-time progress
   - Logs saved to `examples/logs/rca_workflow_YYYYMMDD_HHMMSS.log`
   - Final RCA report with root cause, evidence, and recommendations

## Testing and Quality Assurance

The project includes comprehensive testing infrastructure to ensure reliability:

### Automated Testing
- **Unit tests**: 90%+ code coverage requirement
- **Integration tests**: End-to-end workflow validation
- **Type checking**: 100% MyPy coverage
- **Security scanning**: Bandit + Safety vulnerability checks

### CI/CD Pipeline
```yaml
GitHub Actions workflows:
✓ Code quality: Ruff formatting + linting
✓ Type safety: MyPy static analysis
✓ Test suite: Pytest with coverage reporting
✓ Security: Automated vulnerability scanning
✓ Docker builds: Multi-stage with validation
✓ Container registry: Automatic publishing per branch
```

### Realistic Test Scenarios

The repository includes three carefully crafted tech support scenarios:

1. **BGP MD5 Authentication Failure**
   - Simulated password mismatch on neighbor 10.255.0.2
   - Tests BGP config parsing and log correlation

2. **Syncd Container Crash**
   - Forced syncd daemon failure
   - Tests container log analysis and restart detection

3. **Out-of-Memory Condition**
   - Aggressive memory consumption triggering OOM killer
   - Tests system resource monitoring and panic analysis

Each scenario includes detailed documentation in `test/data/techsupport/README.md`.

## Integration with Existing Tools

The MCP server complements existing SONiC tooling:

### ContainerLab Integration
Pre-built SONiC images for rapid testing:
```yaml
name: sonic-lab
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
```

Available images:
- SONiC 202411 (stable)
- SONiC 202505 (latest)

### MCP Ecosystem
Works with any MCP-compatible client:
- **Claude Desktop**: Native integration for interactive troubleshooting
- **VS Code**: MCP extension for development workflows
- **Custom tools**: Strands Agents, AutoGen, CrewAI, LangChain

## Security and Privacy

The MCP server is designed with security in mind:

- **No external API calls**: All processing happens locally
- **No data exfiltration**: Tech support files never leave your infrastructure
- **Comprehensive logging**: Full audit trail of all operations
- **Controlled access**: MCP protocol provides permission system
- **Open source**: Full code transparency and community review

Perfect for organizations with strict data governance requirements.

## Enterprise Considerations

### Deployment Models

**On-Premises**
- Deploy MCP server on internal jump hosts or bastion servers
- Configure with local LLM endpoints (Ollama, vLLM, etc.)
- Zero external dependencies

**Cloud-Hosted**
- Run in private VPC with API gateway
- Scale horizontally for multiple concurrent analyses
- Integrate with existing SIEM/monitoring systems

**Hybrid**
- Local MCP server, cloud LLM API (with data controls)
- VPN/bastion access for remote engineers
- Centralized logging to compliance systems

### Customization

The modular architecture supports organization-specific customizations:
- **Custom modules**: Add proprietary subsystem analyzers
- **Policy enforcement**: Integrate compliance checking
- **Custom prompts**: Tune analysis tone and depth
- **Output formats**: Generate reports in required formats (JSON, PDF, JIRA tickets)

## Lessons Learned and Future Roadmap

### What We Learned

Through the SONiC Hackathon 2025 development process:

**Successes:**
- Single AI agents excel with clear, specific problem statements
- Multi-agent workflows provide better deep-dive analysis
- MCP integration with Claude Desktop offers excellent UX for interactive troubleshooting
- Regex pattern matching significantly reduces context usage vs. full file reads

**Challenges:**
- Context passing between agents requires careful prompt engineering
- Vague problem statements lead to hallucinations and poor analysis
- Token limits can be hit on extremely verbose logs

### Roadmap

**Short-term (Q1 2025)**
- [ ] Additional modules: VXLAN, ACL, QoS analysis
- [ ] Enhanced resources: Common failure pattern library
- [ ] Performance optimization: Parallel file processing
- [ ] Documentation: Video tutorials and cookbooks

**Medium-term (Q2-Q3 2025)**
- [ ] Real-time analysis: Live device diagnostics (not just dumps)
- [ ] Comparative analysis: Config drift detection across fleet
- [ ] Predictive analytics: Failure prediction from trends
- [ ] Integration packs: ServiceNow, JIRA, PagerDuty

**Long-term (Q4 2025+)**
- [ ] Federated learning: Share anonymized patterns across organizations
- [ ] Automated remediation: Safe, approved fixes executed by agents
- [ ] Proactive monitoring: Continuous analysis of streaming telemetry
- [ ] SONiC certification: Integration with official SONiC testing

## Community and Contributing

This is an open-source project welcoming contributions from the SONiC community:

### Ways to Contribute

**Code Contributions**
- New analysis modules for specific subsystems
- Performance improvements and optimizations
- Additional test scenarios and edge cases
- Bug fixes and documentation updates

**Knowledge Contributions**
- Common failure patterns and resolutions
- Best practices for prompt engineering
- Integration examples with other tools
- Case studies from production usage

**Testing and Feedback**
- Report issues and feature requests
- Share anonymized tech support files for testing
- Provide feedback on analysis accuracy
- Suggest workflow improvements

### Getting Involved

- **GitHub**: [github.com/h4ndzdatm0ld/sonic-nos-mcp](https://github.com/h4ndzdatm0ld/sonic-nos-mcp)
- **ContainerLab Repo**: [github.com/h4ndzdatm0ld/clab-sonic](https://github.com/h4ndzdatm0ld/clab-sonic)
- **Docker Images**: [hub.docker.com/r/h4ndzdatm0ld/sonic-vs](https://hub.docker.com/repository/docker/h4ndzdatm0ld/sonic-vs/general)
- **LinkedIn**: [Hugo Tinoco](https://www.linkedin.com/in/hugo-tinoco)

## Conclusion

The SONiC NOS MCP Server represents a new paradigm in network troubleshooting – one where AI agents work alongside human engineers to rapidly diagnose issues, correlate complex data, and provide consistent, high-quality analysis. By leveraging the Model Context Protocol, we've created a bridge between SONiC's rich diagnostic capabilities and the reasoning power of modern AI models.

Whether you're a network engineer seeking faster troubleshooting, an SRE building automated workflows, or a platform team managing large SONiC deployments, the MCP server offers a flexible, secure, and extensible foundation for AI-assisted network operations.

### Key Takeaways

✅ **Natural language interface** to SONiC tech support analysis  
✅ **Modular architecture** for community extensions  
✅ **Production-ready** with Docker deployment and CI/CD  
✅ **Enterprise-friendly** with local processing and no data exfiltration  
✅ **Open source** with active development and community support  

The future of network troubleshooting is collaborative – human expertise enhanced by AI capabilities, working together through standardized protocols like MCP. We invite you to try the SONiC NOS MCP Server and join us in building the next generation of network operations tools.

---

**About the Author**

Hugo Tinoco is a network automation engineer at Amazon with extensive experience in SONiC deployments, AI/ML applications in networking, and open-source contributions. This project was developed as part of the SONiC Hackathon 2025.

**Resources**

- Project Repository: https://github.com/h4ndzdatm0ld/sonic-nos-mcp
- Model Context Protocol: https://modelcontextprotocol.io
- SONiC Project: https://sonic-net.github.io/SONiC/
- ContainerLab: https://containerlab.dev

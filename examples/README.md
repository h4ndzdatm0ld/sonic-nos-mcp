# SONiC RCA Workflow Examples

This directory contains examples for running SONiC Root Cause Analysis (RCA) workflows using the MCP server tools.

## Prerequisites

Before running these examples, ensure you have:

1. **UV installed** - Fast Python package installer
2. **SONiC NOS MCP server dependencies** - Run `uv sync` from project root
3. **Tech support files** - Sample files are provided in `test/data/techsupport/`

## Quick Start

### BGP Routing Issue Analysis

Analyze BGP neighbor authentication and session establishment problems:

```bash
uv run python examples/invokeWorkflow.py \
  --prompt "BGP neighbor 10.255.0.2 keeps flapping and won't establish session" \
  --tech-support-file test/data/techsupport/techsupport_bgp_md5.tar.gz \
  --verbose
```

**Expected Analysis:** The workflow will examine BGP configuration, authentication settings, neighbor status, and daemon logs to identify MD5 authentication mismatches or other session issues.

### Memory/OOM Issue Analysis

Investigate out-of-memory conditions and system resource exhaustion:

```bash
uv run python examples/invokeWorkflow.py \
  --prompt "System experiencing out of memory conditions" \
  --tech-support-file test/data/techsupport/techsupport_oom.tar.gz \
  --verbose
```

**Expected Analysis:** The workflow will check memory usage, container resource consumption, OOM killer events, and system stability indicators.

### System Crash Analysis

Diagnose process crashes and container restart issues:

```bash
uv run python examples/invokeWorkflow.py \
  --prompt "syncd process keeps crashing" \
  --tech-support-file test/data/techsupport/techsupport_syncd_crash.tar.gz \
  --verbose
```

**Expected Analysis:** The workflow will examine container logs, system events, process status, and crash indicators to determine the root cause.

## Command Options

- `--prompt` (required): The problem statement describing the issue to investigate
- `--tech-support-file` (required): Path to the SONiC tech support archive (`.tar.gz`)
- `--verbose` (optional): Enable detailed logging and debugging output

## How It Works

The RCA workflow follows a systematic 5-step process:

1. **Extract** - Unpack the tech support archive
2. **Discover** - List and categorize available diagnostic files
3. **Analyze** - Examine relevant files based on the problem statement
4. **Correlate** - Cross-reference data across multiple sources
5. **Conclude** - Generate root cause analysis with supporting evidence

## Output

### Console Output
- Real-time progress updates with emoji indicators
- Final root cause analysis summary
- Log file location for detailed review

### Log Files
Detailed logs are automatically saved to `examples/logs/rca_workflow_YYYYMMDD_HHMMSS.log`

## Sample Tech Support Files

The project includes three realistic tech support scenarios:

| File | Scenario | Key Issues |
|------|----------|------------|
| `techsupport_bgp_md5.tar.gz` | BGP Authentication | MD5 password mismatch, neighbor flapping |
| `techsupport_oom.tar.gz` | Memory Exhaustion | Out-of-memory conditions, container restarts |
| `techsupport_syncd_crash.tar.gz` | Process Crashes | syncd daemon crashes, hardware interface issues |

## Troubleshooting

### Common Issues

**"File not found" errors:**
- Verify the tech support file path is correct
- Ensure you're running from the project root directory

**Import errors:**
- Run `uv sync` to install all dependencies
- Ensure the MCP server is properly installed

**Permission errors:**
- Check file permissions on tech support archives
- Ensure write permissions for log directory creation

### Getting Help

Use the `--help` flag to see all available options:

```bash
uv run python examples/invokeWorkflow.py --help
```

## Advanced Usage

### Custom Problem Statements

Be specific in your problem descriptions for better analysis:

```bash
# Good - Specific problem description
--prompt "Interface Ethernet48 shows link flapping with CRC errors in the last hour"

# Less optimal - Vague description
--prompt "Network issues"
```

### Analyzing Your Own Tech Support Files

Replace the sample tech support file with your own:

```bash
uv run python examples/invokeWorkflow.py \
  --prompt "Your specific problem description" \
  --tech-support-file /path/to/your/techsupport.tar.gz \
  --verbose
```

## Development Notes

This workflow system is part of the SONiC MCP Hackathon 2025 project, demonstrating how MCP servers can provide intelligent diagnostic analysis for network device troubleshooting.

The sequential agent approach breaks down complex RCA tasks into manageable steps, making the analysis process more transparent and reliable than monolithic approaches.

# Product Context - SONiC NOS MCP Server

## Why This Project Exists

### Problem Statement
Network engineers and support teams working with SONiC (Software for Open Networking in the Cloud) devices need efficient tools to analyze diagnostic bundles when troubleshooting network issues. These tech support files contain vast amounts of system state, configuration, and logging data that require specialized knowledge to navigate and interpret effectively.

### Current Challenges
- **Manual Analysis**: Engineers manually extract and navigate through complex directory structures
- **File Format Complexity**: Multiple file formats (JSON databases, compressed logs, system dumps)
- **Information Overload**: Hundreds of files with varying importance and relevance
- **Tool Fragmentation**: No unified interface for SONiC diagnostic analysis
- **Knowledge Barriers**: Requires deep understanding of SONiC file structure and contents

## Problems This Project Solves

### 1. Unified Analysis Interface
- Single MCP server providing all necessary tools for SONiC tech support analysis
- Consistent API across different types of diagnostic operations
- Integration with modern development environments through MCP protocol

### 2. Automated Processing
- **Extraction**: Automatically extract tech support archives (tar.gz, zip)
- **Navigation**: Intelligent file listing with filtering capabilities
- **Content Analysis**: Regex-based pattern matching across files
- **Pagination**: Handle large files efficiently with chunked reading

### 3. Domain Knowledge Integration
- Built-in understanding of SONiC file structures
- Educational resources about tech support file organization
- Contextual guidance for different types of network issues

## How It Should Work

### User Experience Goals

#### 1. Simple Extraction Workflow
```
1. User provides path to SONiC tech support archive
2. MCP server extracts to temporary directory
3. Server returns organized file listing
4. User can immediately start analyzing specific files
```

#### 2. Intelligent File Navigation
```
- Filter files by directory (dump/, log/, etc/)
- Search by file patterns (*.json, syslog*, etc.)
- Understand key files for specific troubleshooting scenarios
```

#### 3. Content Analysis
```
- Read any file with automatic decompression
- Search content with regex patterns
- Handle large files with pagination
- Extract relevant sections efficiently
```

### Target Workflows

#### Network Troubleshooting Scenario
1. **Extract** tech support file from device
2. **List** files to understand available diagnostic data
3. **Inspect** interface status files for connectivity issues
4. **Search** logs for error patterns and timeline reconstruction
5. **Analyze** database dumps for configuration vs. operational state

#### System Health Analysis
1. **Extract** diagnostic bundle
2. **Examine** system health databases (STATE_DB.json)
3. **Review** hardware sensor data and alerts
4. **Correlate** events across multiple log files
5. **Generate** summary of system status

## Integration Goals

### MCP Client Integration
- Seamless integration with VS Code through MCP extensions
- Command palette access to all SONiC analysis tools
- Contextual help and guidance within development environment

### Workflow Automation
- Enable scripted analysis through MCP protocol
- Support batch processing of multiple tech support files
- Facilitate automated report generation

### Knowledge Sharing
- Embedded educational content about SONiC diagnostics
- Best practices for network troubleshooting
- Guidance on interpreting SONiC system state

## User Value Proposition

### For Network Engineers
- Reduce diagnostic time from hours to minutes
- Access to expert knowledge embedded in tools
- Consistent analysis methodology across teams

### For Support Teams
- Streamlined customer issue resolution
- Automated extraction and initial analysis
- Clear documentation of investigation steps

### For DevOps Teams
- Integration with existing automation workflows
- Scriptable diagnostic procedures
- Standardized troubleshooting processes

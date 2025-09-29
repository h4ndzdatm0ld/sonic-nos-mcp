# System Patterns - SONiC NOS MCP Server

## Architecture Overview

The SONiC NOS MCP Server implements a modular plugin architecture that allows for extensible tools and resources while maintaining a clean separation of concerns.

## System Architecture

### Core Components

```
sonic_nos_mcp/
├── server.py              # Main MCP server entry point
├── module_base.py         # Base class for all modules  
├── module_registry.py     # Module registration system
└── modules/               # Pluggable modules directory
    └── tech_support/      # Tech support analysis module
        ├── module.py      # Module implementation
        ├── models/        # Pydantic data models
        ├── tools/         # MCP tool implementations  
        └── utils/         # Core business logic
```

### Key Design Patterns

#### 1. Plugin Architecture
- **ModuleRegistry**: Central registry for all modules
- **ModuleBase**: Abstract base class defining module interface
- **Auto-registration**: Modules self-register through imports
- **Dynamic Loading**: Server discovers and loads modules at runtime

#### 2. Separation of Concerns
- **Models**: Pydantic models for request/response validation
- **Tools**: MCP tool decorators and user-facing interfaces
- **Utils**: Core business logic separate from MCP concerns
- **Resources**: Static educational content and documentation

#### 3. Request/Response Pattern
```python
# Consistent pattern across all tools:
Request → Validation → Business Logic → Response → MCP Result
```

## Module Structure Pattern

### Standard Module Layout
```
modules/{module_name}/
├── __init__.py
├── module.py              # Module class with tool registration
├── models/                # Pydantic request/response models
│   ├── __init__.py
│   ├── {operation}_models.py
├── tools/                 # MCP tool implementations
│   ├── __init__.py  
│   └── {operation}_tool.py
└── utils/                 # Business logic utilities
    ├── __init__.py
    └── {operation}.py
```

### Module Registration Flow
1. Module imports trigger side effects
2. Module class extends ModuleBase
3. ModuleRegistry.register() adds to registry
4. Server discovers modules via registry
5. Server calls register_tools() for each module

## Tech Support Module Patterns

### Tool Implementation Pattern
```python
@mcp.tool(description="...")
def tool_name(
    param: Annotated[Type, Field(description="...")]
) -> dict:
    # 1. Create request model
    request = RequestModel(param=param)
    
    # 2. Call business logic
    response = business_logic_function(request)
    
    # 3. Convert to MCP response
    return response.to_dict()
```

### Business Logic Separation
- **Tools**: Handle MCP decorators and parameter validation
- **Utils**: Implement core functionality independently of MCP
- **Models**: Define data structures for type safety

### Error Handling Pattern
```python
try:
    # Business logic
    result = perform_operation()
    return {"success": True, "data": result}
except Exception as e:
    logger.exception(f"Operation failed: {e}")
    return {"success": False, "error_message": str(e)}
```

## Resource Pattern

### Educational Resources
- **Static Content**: Embedded documentation and guides
- **URI Scheme**: Custom scheme for resource identification (e.g., `sonic://tech-support-guide`)
- **Comprehensive Guides**: Complete reference materials for users

### Resource Registration
```python
@mcp.resource("sonic://resource-name")
def get_resource() -> str:
    return """# Resource Content
    
    Comprehensive guide content here...
    """
```

## Data Flow Patterns

### File Processing Pipeline
```
Archive File → Extraction → File Listing → Content Analysis
     ↓             ↓            ↓              ↓
   Validation → Temp Dir → Pattern Match → Chunked Output
```

### Pagination Pattern
- **Large File Handling**: Automatic chunking for large files
- **Page-based Access**: Page parameter for content navigation  
- **Memory Efficiency**: Avoid loading entire large files
- **Progress Tracking**: Total pages and current page information

## Error Recovery Patterns

### Graceful Degradation
- Continue processing even if individual files fail
- Provide partial results with error information
- Log errors for debugging while maintaining user experience

### Validation Strategy  
- **Input Validation**: Pydantic models validate all inputs
- **File Existence**: Check file paths before processing
- **Format Detection**: Automatic archive format detection
- **Compression Handling**: Transparent decompression

## Extension Points

### Adding New Modules
1. Create module directory following standard layout
2. Implement ModuleBase subclass
3. Register tools and resources in register_tools()
4. Import module in server.py for auto-registration

### Adding New Tools to Existing Modules
1. Create request/response models in models/
2. Implement business logic in utils/
3. Create tool wrapper in tools/
4. Register tool in module.py

## Critical Implementation Paths

### 1. Tech Support File Extraction
- **Extract Tool**: Handle multiple archive formats
- **Temp Directory**: Safe temporary file management
- **File Listing**: Recursive directory traversal
- **Pattern Matching**: Glob-based file filtering

### 2. Content Analysis  
- **File Reading**: Handle compressed and text files
- **Regex Processing**: Pattern matching with context
- **Pagination**: Chunk large files for manageable output
- **Performance**: Avoid memory issues with large files

### 3. Educational Integration
- **SONiC Knowledge**: Embedded understanding of file structures
- **Troubleshooting Guidance**: Contextual help for common scenarios
- **Best Practices**: Documentation of analysis workflows

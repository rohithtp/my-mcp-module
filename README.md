# MCP Python Client Module

A Python client module for interacting with the Model Context Protocol (MCP) server. This module provides a clean interface to list and invoke MCP tools.

## Features

- Environment-based configuration
- Automatic virtual environment management using `uv`
- Tool discovery and invocation
- Session management and connection reuse
- Comprehensive error handling and logging
- Context manager support

## Prerequisites

- Python 3.9 or higher
- `uv` package manager installed
- Access to an MCP server (default: http://localhost:3000)

## Installation

1. Clone the repository (if not already part of the main project):
   ```bash
   git clone <repository-url>
   cd my_mcp_module
   ```

2. Set up the virtual environment and install dependencies:
   ```bash
   ./scripts/setup_venv.sh
   ```

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` to configure your MCP server URL:
   ```
   MCP_SERVER_URL=http://localhost:3000
   ```

## Usage

### Basic Example

```python
from my_mcp_module.mcp_client import MCPClient

# Using context manager (recommended)
with MCPClient() as client:
    # List available tools
    tools = client.get_tools()
    
    # Invoke a specific tool
    result = client.invoke_tool("tool_name", {
        "param1": "value1",
        "param2": "value2"
    })

# Manual instantiation
client = MCPClient()
try:
    tools = client.get_tools()
finally:
    client.close()
```

### Running Examples

The module includes example scripts in the `examples/` directory:

```bash
# List available MCP tools
./examples/list_tools.py
```

### Directory Structure

```
my_mcp_module/
├── .env.example          # Environment configuration template
├── pyproject.toml        # Project metadata and dependencies
├── README.md            # This documentation
├── src/
│   └── my_mcp_module/
│       └── mcp_client.py # Main client implementation
├── examples/            # Example scripts
│   └── list_tools.py    # Tool listing example
├── scripts/             # Utility scripts
│   ├── setup_venv.sh    # Virtual environment setup
│   └── run_in_venv.sh   # venv execution wrapper
└── tests/               # Test directory
```

## Development

### Virtual Environment

The project uses `uv` for package management and virtual environments. The included scripts handle this automatically:

- `scripts/setup_venv.sh`: Creates and configures the virtual environment
- `scripts/run_in_venv.sh`: Ensures commands run within the virtual environment

### Dependencies

Project dependencies are managed in `pyproject.toml`:

- `requests`: HTTP client for API communication
- `python-dotenv`: Environment file management

### API Reference

#### MCPClient

Main client class for interacting with the MCP server.

```python
class MCPClient:
    def __init__(self, env_file: Optional[str] = None):
        """Initialize the MCP client.
        
        Args:
            env_file: Optional path to environment file
        """

    def get_tools(self) -> List[MCPTool]:
        """Retrieve available tools from the MCP server."""

    def invoke_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Invoke an MCP tool with parameters."""

    def close(self):
        """Close the client session."""
```

#### MCPTool

Data class representing an MCP tool configuration.

```python
@dataclass
class MCPTool:
    name: str           # Tool name
    description: str    # Tool description
    parameters: Dict    # Tool parameters
    required_params: List[str]  # Required parameter names
```

## Error Handling

The client includes comprehensive error handling:

- Environment configuration errors
- HTTP request failures
- Tool invocation errors
- Invalid parameter errors

All errors are logged using Python's standard logging module.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Add your license information here] 
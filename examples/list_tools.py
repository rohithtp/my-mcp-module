#!/usr/bin/env bash
"$(dirname "$0")/../scripts/run_in_venv.sh" python3 - "$@" << 'EOF'
"""Example script demonstrating how to use the MCP client to list available tools."""

from my_mcp_module.mcp_client import MCPClient

def main():
    """Main function to demonstrate MCP client usage."""
    # Create an MCP client instance
    with MCPClient() as client:
        try:
            # Get available tools
            tools = client.get_tools()
            
            print("\nAvailable MCP Tools:")
            print("===================")
            
            for tool in tools:
                print(f"\nTool: {tool.name}")
                print(f"Description: {tool.description}")
                print("Parameters:")
                for param_name, param_info in tool.parameters.items():
                    required = "Required" if param_name in tool.required_params else "Optional"
                    print(f"  - {param_name}: {required}")
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
EOF 
"""MCP Client Module for interacting with the MCP server."""

import os
import json
import logging
import uuid
import sseclient
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MCPTool:
    """Represents an MCP tool configuration."""
    name: str
    description: str
    parameters: Dict[str, Any]
    required_params: List[str]

class MCPClient:
    """Client for interacting with the MCP server."""
    
    def __init__(self, env_file: Optional[str] = None, session_id: Optional[str] = None):
        """Initialize the MCP client.
        
        Args:
            env_file: Path to the environment file. If None, looks for .env in the current directory.
            session_id: Optional session ID. If None, a new UUID will be generated.
        """
        if env_file:
            load_dotenv(env_file)
        else:
            # Look for .env in the current directory and parent directories
            current_dir = Path.cwd()
            env_path = None
            
            while current_dir.parent != current_dir:
                test_path = current_dir / '.env'
                if test_path.exists():
                    env_path = test_path
                    break
                current_dir = current_dir.parent
            
            if env_path:
                load_dotenv(env_path)
            else:
                logger.warning("No .env file found. Using default configuration.")
        
        self.server_url = os.getenv('MCP_SERVER_URL', 'http://localhost:3000')
        self.session_id = session_id or str(uuid.uuid4())
        logger.info(f"Initialized MCP client with server URL: {self.server_url} and session ID: {self.session_id}")
        
        # Initialize session for connection reuse
        self.session = requests.Session()
        
        # Initialize the connection
        self._initialize_connection()
        
    def _initialize_connection(self):
        """Initialize the connection with the MCP server."""
        # Send initialize request
        init_payload = {
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "prompts": {},
                    "resources": {},
                    "tools": {}
                },
                "clientInfo": {
                    "name": "python-mcp-client",
                    "version": "1.0.0"
                }
            },
            "jsonrpc": "2.0",
            "id": 0
        }
        
        response = self.session.post(
            f"{self.server_url}/message?sessionId={self.session_id}",
            json=init_payload,
            headers={
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'Accept-Language': '*',
                'Sec-Fetch-Mode': 'cors',
                'User-Agent': 'node',
                'Accept-Encoding': 'gzip, deflate'
            }
        )
        
        if response.status_code == 202:
            logger.info("Initialization request accepted")
            
            # Send initialized notification
            notify_payload = {
                "method": "notifications/initialized",
                "jsonrpc": "2.0"
            }
            
            response = self.session.post(
                f"{self.server_url}/message?sessionId={self.session_id}",
                json=notify_payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': '*/*',
                    'Accept-Language': '*',
                    'Sec-Fetch-Mode': 'cors',
                    'User-Agent': 'node',
                    'Accept-Encoding': 'gzip, deflate'
                }
            )
            
            if response.status_code == 202:
                logger.info("Initialized notification sent")
            else:
                raise requests.exceptions.RequestException(f"Failed to send initialized notification: {response.status_code}")
        else:
            raise requests.exceptions.RequestException(f"Failed to initialize connection: {response.status_code}")
    
    def get_tools(self) -> List[MCPTool]:
        """Retrieve available tools from the MCP server.
        
        Returns:
            List of available MCP tools.
        
        Raises:
            requests.exceptions.RequestException: If the server request fails.
        """
        try:
            payload = {
                "method": "tools/list",
                "jsonrpc": "2.0",
                "id": 1
            }
            logger.info(f"Sending request to {self.server_url}/message with payload: {json.dumps(payload)}")
            
            response = self.session.post(
                f"{self.server_url}/message?sessionId={self.session_id}",
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': '*/*',
                    'Accept-Language': '*',
                    'Sec-Fetch-Mode': 'cors',
                    'User-Agent': 'node',
                    'Accept-Encoding': 'gzip, deflate'
                }
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if response.content:
                logger.info(f"Response content: {response.content.decode()}")
            
            if response.status_code == 202:
                logger.info("Request accepted, connecting to SSE stream...")
                # Connect to SSE stream
                sse_response = self.session.get(
                    f"{self.server_url}/events?sessionId={self.session_id}",
                    stream=True,
                    headers={
                        'Accept': 'text/event-stream',
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive'
                    }
                )
                
                client = sseclient.SSEClient(sse_response)
                for event in client.events():
                    if event.data:
                        data = json.loads(event.data)
                        if isinstance(data, dict) and 'tools' in data:
                            tools = []
                            for tool_data in data['tools']:
                                tool = MCPTool(
                                    name=tool_data['name'],
                                    description=tool_data.get('description', ''),
                                    parameters=tool_data.get('parameters', {}),
                                    required_params=tool_data.get('required', [])
                                )
                                tools.append(tool)
                            return tools
                return []
            
            response.raise_for_status()
            
            result = response.json()
            if 'error' in result:
                raise requests.exceptions.RequestException(f"RPC Error: {result['error']}")
                
            tools_data = result.get('result', [])
            tools = []
            
            for tool_data in tools_data:
                tool = MCPTool(
                    name=tool_data['name'],
                    description=tool_data.get('description', ''),
                    parameters=tool_data.get('parameters', {}),
                    required_params=tool_data.get('required', [])
                )
                tools.append(tool)
            
            return tools
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve tools from MCP server: {e}")
            raise
    
    def invoke_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Invoke an MCP tool with the given parameters.
        
        Args:
            tool_name: Name of the tool to invoke.
            parameters: Parameters to pass to the tool.
            
        Returns:
            Tool execution result.
            
        Raises:
            requests.exceptions.RequestException: If the server request fails.
        """
        try:
            payload = {
                "method": tool_name,
                "jsonrpc": "2.0",
                "id": 1,
                "params": parameters
            }
            logger.info(f"Sending request to {self.server_url}/message with payload: {json.dumps(payload)}")
            
            response = self.session.post(
                f"{self.server_url}/message?sessionId={self.session_id}",
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': '*/*',
                    'Accept-Language': '*',
                    'Sec-Fetch-Mode': 'cors',
                    'User-Agent': 'node',
                    'Accept-Encoding': 'gzip, deflate'
                }
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if response.content:
                logger.info(f"Response content: {response.content.decode()}")
            
            if response.status_code == 202:
                logger.info("Request accepted, waiting for response...")
                # TODO: Implement polling or WebSocket connection for actual response
                return None
            
            response.raise_for_status()
            
            result = response.json()
            if 'error' in result:
                raise requests.exceptions.RequestException(f"RPC Error: {result['error']}")
            
            return result.get('result')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to invoke tool {tool_name}: {e}")
            if isinstance(e, requests.exceptions.Timeout):
                logger.error("Request timed out after 30 seconds")
            raise
    
    def close(self):
        """Close the client session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close() 
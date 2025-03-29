"""MCP Client Module for interacting with the MCP server."""

import os
import json
import logging
import uuid
import time
import threading
import queue
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
        
        # Initialize response queue for SSE events
        self.response_queue = queue.Queue()
        self.session_id_event = threading.Event()
        
        # Initialize the connection
        self._initialize_connection()
    
    def _start_sse_listener(self):
        """Start listening for SSE events."""
        headers = {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
        
        response = self.session.get(
            f"{self.server_url}/sse?sessionId={self.session_id}",
            headers=headers,
            stream=True
        )
        
        if response.status_code != 200:
            raise requests.exceptions.RequestException(f"Failed to establish SSE connection: {response.status_code}")
        
        client = sseclient.SSEClient(response)
        
        def _listen():
            for event in client.events():
                logger.debug(f"Received SSE event: {event.event} - {event.data}")
                if event.event == 'endpoint':
                    # Extract session ID from the endpoint URL
                    endpoint_url = event.data.strip()
                    new_session_id = endpoint_url.split('sessionId=')[1]
                    self.session_id = new_session_id
                    logger.info(f"Updated session ID to: {self.session_id}")
                    self.session_id_event.set()
                elif event.event == 'response':
                    try:
                        data = json.loads(event.data)
                        self.response_queue.put(data)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse response data: {event.data}")
        
        self.sse_thread = threading.Thread(target=_listen, daemon=True)
        self.sse_thread.start()
        
        # Wait for the session ID to be updated
        if not self.session_id_event.wait(timeout=5):
            raise requests.exceptions.RequestException("Timed out waiting for session ID from SSE")
    
    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None, request_id: Optional[int] = None) -> Dict[str, Any]:
        """Send a request to the server and wait for response."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id if request_id is not None else 0
        }
        if params is not None:
            payload["params"] = params
        
        logger.info(f"Sending request: {json.dumps(payload)}")
        
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
        
        if response.status_code == 202:
            logger.info("Request accepted, waiting for response...")
            try:
                result = self.response_queue.get(timeout=5)
                logger.info(f"Response received: {result}")
                if 'error' in result:
                    raise requests.exceptions.RequestException(f"RPC Error: {result['error']}")
                return result.get('result', {})
            except queue.Empty:
                raise requests.exceptions.RequestException("Timed out waiting for response")
        else:
            raise requests.exceptions.RequestException(f"Request failed: {response.status_code}")
    
    def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Send a notification to the server."""
        payload = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params is not None:
            payload["params"] = params
        
        logger.info(f"Sending notification: {json.dumps(payload)}")
        
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
        
        if response.status_code != 202:
            raise requests.exceptions.RequestException(f"Failed to send notification: {response.status_code}")
    
    def _initialize_connection(self):
        """Initialize the connection with the MCP server."""
        # Start SSE listener first and wait for session ID
        self._start_sse_listener()
        
        # Step 1: Send initialize request
        init_result = self._send_request(
            "$/initialize",
            {
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
            request_id=0
        )
        
        logger.info(f"Server capabilities: {init_result}")
        
        # Step 2: Send initialized notification
        self._send_notification("$/initialized")
        
        logger.info("Connection initialized successfully")
    
    def get_tools(self) -> List[MCPTool]:
        """Retrieve available tools from the MCP server.
        
        Returns:
            List of available MCP tools.
        
        Raises:
            requests.exceptions.RequestException: If the server request fails.
        """
        try:
            result = self._send_request("$/tools/list", request_id=1)
            tools = []
            
            for tool_data in result:
                tool = MCPTool(
                    name=tool_data['name'],
                    description=tool_data.get('description', ''),
                    parameters=tool_data.get('parameters', {}),
                    required_params=tool_data.get('required', [])
                )
                tools.append(tool)
            
            return tools
            
        except Exception as e:
            logger.error(f"Error getting tools: {str(e)}")
            raise
    
    def close(self):
        """Close the connection with the MCP server."""
        try:
            self._send_notification("$/shutdown")
            logger.info("Successfully closed connection")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error while closing connection: {str(e)}")
        finally:
            self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close() 
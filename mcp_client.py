import requests
import json
import uuid
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class MCPTool:
    name: str
    description: str
    parameters: Dict[str, Any]

class MCPClient:
    def __init__(self, server_url: str = "http://localhost:3000", session_id: Optional[str] = None):
        self.server_url = server_url.rstrip('/')
        self.session_id = session_id or str(uuid.uuid4())
        self.headers = {
            'Content-Type': 'application/json',
            'X-MCP-Session-ID': self.session_id
        }
        logger.info(f"Initialized MCP client with server URL: {server_url} and session ID: {self.session_id}")

    def __enter__(self):
        self._initialize_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _initialize_connection(self):
        """Initialize connection with the MCP server."""
        init_data = {
            'session_id': self.session_id,
            'client_type': 'python',
            'client_version': '1.0.0'
        }
        
        try:
            response = requests.post(
                f"{self.server_url}/initialize",
                headers=self.headers,
                json=init_data,
                timeout=30
            )
            
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"Failed to initialize connection: {response.status_code} {response.text}"
                )
            logger.info("Successfully initialized connection")
            
        except requests.exceptions.Timeout:
            raise requests.exceptions.RequestException(
                "Connection initialization timed out. Server may be busy or unreachable."
            )
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(
                f"Failed to initialize connection: {str(e)}"
            )

    def invoke_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool with the given parameters."""
        request_data = {
            'tool': tool_name,
            'parameters': parameters
        }

        try:
            response = requests.post(
                f"{self.server_url}/invoke",
                headers=self.headers,
                json=request_data,
                timeout=30
            )

            if response.status_code == 202:
                # Server accepted the request, now poll for result
                return self._poll_for_result()
            
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"Tool invocation failed: {response.status_code} {response.text}"
                )

            return response.json()
            
        except requests.exceptions.Timeout:
            raise requests.exceptions.RequestException(
                "Tool invocation timed out. Server may be busy or unreachable."
            )
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(
                f"Tool invocation failed: {str(e)}"
            )

    def _poll_for_result(self, max_retries: int = 10, delay: float = 1.0) -> Dict[str, Any]:
        """Poll for result of an asynchronous tool invocation."""
        import time
        
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f"{self.server_url}/result/{self.session_id}",
                    headers=self.headers,
                    timeout=30
                )

                if response.status_code == 200:
                    return response.json()
                
                if response.status_code != 202:
                    raise requests.exceptions.RequestException(
                        f"Failed to get result: {response.status_code} {response.text}"
                    )
                
                time.sleep(delay)
                
            except requests.exceptions.Timeout:
                logger.warning(f"Polling attempt {attempt + 1} timed out")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Polling attempt {attempt + 1} failed: {str(e)}")

        raise TimeoutError("Maximum retries reached while polling for result")

    def get_tools(self) -> Dict[str, MCPTool]:
        """Get available tools from the server."""
        try:
            response = requests.get(
                f"{self.server_url}/tools",
                headers=self.headers,
                timeout=30
            )

            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"Failed to get tools: {response.status_code} {response.text}"
                )

            tools_data = response.json()
            return {
                name: MCPTool(
                    name=name,
                    description=tool['description'],
                    parameters=tool['parameters']
                )
                for name, tool in tools_data.items()
            }
            
        except requests.exceptions.Timeout:
            raise requests.exceptions.RequestException(
                "Failed to get tools: request timed out"
            )
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(
                f"Failed to get tools: {str(e)}"
            )

    def close(self):
        """Close the connection with the MCP server."""
        try:
            response = requests.post(
                f"{self.server_url}/close",
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                logger.info("Successfully closed connection")
            else:
                logger.warning(f"Failed to close connection: {response.status_code} {response.text}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error while closing connection: {str(e)}") 
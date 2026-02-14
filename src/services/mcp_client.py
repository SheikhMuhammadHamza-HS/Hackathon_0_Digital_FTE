"""MCP Client for communicating with MCP servers.

This module provides a Python client to interact with MCP servers
for email and LinkedIn operations.
"""

import json
import logging
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for communicating with MCP servers via stdio."""

    def __init__(self, server_name: str, config: Dict[str, Any]):
        """Initialize MCP client for a specific server.

        Args:
            server_name: Name of the MCP server (e.g., 'email-mcp', 'linkedin-mcp')
            config: Server configuration from mcp.json
        """
        self.server_name = server_name
        self.config = config
        self.process = None
        self._request_id = 0

    def start(self) -> bool:
        """Start the MCP server process.

        Returns:
            True if server started successfully, False otherwise
        """
        try:
            command = self.config.get('command', 'node')
            args = self.config.get('args', [])
            env = self.config.get('env', {})

            # Merge with current environment
            import os
            full_env = os.environ.copy()
            full_env.update(env)

            logger.info(f"Starting MCP server: {self.server_name}")
            self.process = subprocess.Popen(
                [command] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
                env=full_env
            )

            # Initialize the connection
            self._send_request({
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "digital-fte",
                        "version": "1.0.0"
                    }
                }
            })

            # Send initialized notification
            self._send_notification({
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            })

            logger.info(f"MCP server {self.server_name} started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start MCP server {self.server_name}: {e}")
            return False

    def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC request to the MCP server.

        Args:
            request: JSON-RPC request object

        Returns:
            Response from the server, or None on failure
        """
        if not self.process or self.process.poll() is not None:
            logger.error(f"MCP server {self.server_name} is not running")
            return None

        try:
            # Send request
            request_str = json.dumps(request) + '\n'
            self.process.stdin.write(request_str)
            self.process.stdin.flush()

            # Read response
            response_line = self.process.stdout.readline()
            if not response_line:
                logger.error(f"No response from MCP server {self.server_name}")
                return None

            response = json.loads(response_line)
            return response

        except Exception as e:
            logger.error(f"Error communicating with MCP server {self.server_name}: {e}")
            return None

    def _send_notification(self, notification: Dict[str, Any]) -> bool:
        """Send a JSON-RPC notification (no response expected).

        Args:
            notification: JSON-RPC notification object

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.process or self.process.poll() is not None:
            return False

        try:
            notification_str = json.dumps(notification) + '\n'
            self.process.stdin.write(notification_str)
            self.process.stdin.flush()
            return True
        except Exception as e:
            logger.error(f"Error sending notification to MCP server {self.server_name}: {e}")
            return False

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool result, or None on failure
        """
        self._request_id += 1

        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        response = self._send_request(request)
        if response and 'result' in response:
            return response['result']
        elif response and 'error' in response:
            logger.error(f"Tool {tool_name} returned error: {response['error']}")
            return None

        return None

    def list_tools(self) -> Optional[list]:
        """List available tools on the MCP server.

        Returns:
            List of available tools, or None on failure
        """
        self._request_id += 1

        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/list",
            "params": {}
        }

        response = self._send_request(request)
        if response and 'result' in response:
            return response['result'].get('tools', [])
        return None

    def stop(self):
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            logger.info(f"MCP server {self.server_name} stopped")


class MCPManager:
    """Manager for multiple MCP servers."""

    def __init__(self, config_path: Path):
        """Initialize MCP manager from configuration file.

        Args:
            config_path: Path to mcp.json configuration file
        """
        self.config_path = config_path
        self.clients: Dict[str, MCPClient] = {}
        self._load_config()

    def _load_config(self):
        """Load MCP configuration from file."""
        if not self.config_path.exists():
            logger.warning(f"MCP config not found at {self.config_path}")
            return

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            servers = config.get('mcpServers', {})
            for server_name, server_config in servers.items():
                self.clients[server_name] = MCPClient(server_name, server_config)

            logger.info(f"Loaded {len(self.clients)} MCP server configurations")

        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")

    def get_client(self, server_name: str) -> Optional[MCPClient]:
        """Get a client for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            MCPClient instance or None if server not found
        """
        client = self.clients.get(server_name)
        if client and (client.process is None or client.process.poll() is not None):
            # Start the server if not running
            if client.start():
                return client
            return None

        return client

    def start_all(self) -> Dict[str, bool]:
        """Start all configured MCP servers.

        Returns:
            Dictionary mapping server names to start success status
        """
        results = {}
        for server_name, client in self.clients.items():
            results[server_name] = client.start()
        return results

    def stop_all(self):
        """Stop all running MCP servers."""
        for client in self.clients.values():
            client.stop()


# Global MCP manager instance
_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """Get the global MCP manager instance.

    Returns:
        MCPManager instance
    """
    global _mcp_manager

    if _mcp_manager is None:
        # Try to find mcp.json in common locations
        possible_paths = [
            Path('mcp.json'),
            Path('.claude/mcp.json'),
            Path.home() / '.config' / 'claude-code' / 'mcp.json',
        ]

        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break

        if config_path:
            _mcp_manager = MCPManager(config_path)
        else:
            logger.warning("No mcp.json configuration file found")
            _mcp_manager = MCPManager(Path('mcp.json'))

    return _mcp_manager
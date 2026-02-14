# MCP Servers for Digital FTE

This directory contains Model Context Protocol (MCP) servers that enable the Digital FTE to interact with external services.

## Available Servers

### email-mcp
Handles email operations via Gmail API.

**Tools:**
- `send_email` - Send an email via Gmail API
- `get_profile` - Get the authenticated user's Gmail profile

**Setup:**
1. Install dependencies: `cd email-mcp && npm install`
2. Set `GMAIL_TOKEN` environment variable with your Gmail OAuth2 credentials
3. Server is automatically started by the MCP client when needed

### linkedin-mcp
Handles LinkedIn posting operations.

**Tools:**
- `create_post` - Create a LinkedIn post
- `get_profile` - Get the authenticated user's LinkedIn profile

**Setup:**
1. Install dependencies: `cd linkedin-mcp && npm install`
2. Set `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_USER_ID` environment variables
3. Server is automatically started by the MCP client when needed

## Configuration

MCP servers are configured in `mcp.json` at the project root. The configuration includes:

- Server command and arguments
- Environment variables for credentials
- Timeout and retry settings

## Usage

The MCP client (`src/services/mcp_client.py`) automatically manages server lifecycle:

```python
from src.services.mcp_client import get_mcp_manager

# Get the MCP manager
manager = get_mcp_manager()

# Get a client for a specific server
client = manager.get_client('email-mcp')

# Call a tool
result = client.call_tool('send_email', {
    'to': 'recipient@example.com',
    'subject': 'Test Email',
    'body': 'Hello from MCP!'
})
```

## Architecture

```
Digital FTE (Python)
    ↓
MCP Client (src/services/mcp_client.py)
    ↓ (stdio communication)
MCP Server (Node.js)
    ↓
External API (Gmail, LinkedIn, etc.)
```

## Benefits

1. **Separation of Concerns**: API logic is isolated in MCP servers
2. **Security**: Credentials are managed by MCP servers, not the main application
3. **Flexibility**: Easy to add new servers for different services
4. **Mock Mode**: Falls back to mock mode if servers are unavailable
5. **Standard Protocol**: Uses the Model Context Protocol for interoperability

## Troubleshooting

**Server not starting:**
- Check that Node.js is installed: `node --version`
- Install dependencies: `npm install` in the server directory
- Check environment variables are set correctly

**Tool calls failing:**
- Verify credentials are valid
- Check server logs for error messages
- Ensure the server is running and responding

**Connection issues:**
- Check that the server path in `mcp.json` is correct
- Verify the server command is executable
- Check for port conflicts if applicable
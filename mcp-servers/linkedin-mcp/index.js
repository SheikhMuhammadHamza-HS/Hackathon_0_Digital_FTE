#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';

// LinkedIn API configuration
const LINKEDIN_API_BASE = 'https://api.linkedin.com/v2';

// Get LinkedIn credentials from environment
const LINKEDIN_ACCESS_TOKEN = process.env.LINKEDIN_ACCESS_TOKEN;
const LINKEDIN_USER_ID = process.env.LINKEDIN_USER_ID;

// Create MCP Server
const server = new Server(
  {
    name: 'linkedin-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'create_post',
        description: 'Create a LinkedIn post',
        inputSchema: {
          type: 'object',
          properties: {
            text: {
              type: 'string',
              description: 'Post content text',
            },
            visibility: {
              type: 'string',
              enum: ['PUBLIC', 'CONNECTIONS'],
              description: 'Post visibility (default: PUBLIC)',
            },
          },
          required: ['text'],
        },
      },
      {
        name: 'get_profile',
        description: 'Get the authenticated user\'s LinkedIn profile',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
    ],
  };
});

// Helper function to make authenticated LinkedIn API calls
async function linkedinApiCall(endpoint, method = 'GET', data = null) {
  if (!LINKEDIN_ACCESS_TOKEN) {
    throw new Error('LINKEDIN_ACCESS_TOKEN environment variable not set');
  }

  try {
    const config = {
      method,
      url: `${LINKEDIN_API_BASE}${endpoint}`,
      headers: {
        'Authorization': `Bearer ${LINKEDIN_ACCESS_TOKEN}`,
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0',
      },
    };

    if (data && (method === 'POST' || method === 'PUT')) {
      config.data = data;
    }

    const response = await axios(config);
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(`LinkedIn API error: ${error.response.status} - ${JSON.stringify(error.response.data)}`);
    }
    throw new Error(`LinkedIn API request failed: ${error.message}`);
  }
}

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'create_post': {
        const { text, visibility = 'PUBLIC' } = args;

        if (!text) {
          throw new Error('Missing required parameter: text');
        }

        // Get user URN if not provided
        const userId = LINKEDIN_USER_ID || `person:${(await linkedinApiCall('/me')).id}`;

        // Create the post
        const postData = {
          author: `urn:li:${userId}`,
          lifecycleState: 'PUBLISHED',
          specificContent: {
            'com.linkedin.ugc.ShareContent': {
              shareCommentary: {
                text: text,
              },
              shareMediaCategory: 'NONE',
            },
          },
          visibility: {
            'com.linkedin.ugc.MemberNetworkVisibility': visibility,
          },
        };

        const response = await linkedinApiCall('/ugcPosts', 'POST', postData);

        return {
          content: [
            {
              type: 'text',
              text: `LinkedIn post created successfully! Post ID: ${response.id}`,
            },
          ],
        };
      }

      case 'get_profile': {
        const profile = await linkedinApiCall('/me?projection=(id,firstName,lastName,headline,profilePicture(displayImage~:playableStreams))');

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                id: profile.id,
                localized_first_name: profile.firstName.localized.en_US,
                localized_last_name: profile.lastName.localized.en_US,
                headline: profile.headline,
              }, null, 2),
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error executing ${name}: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('LinkedIn MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
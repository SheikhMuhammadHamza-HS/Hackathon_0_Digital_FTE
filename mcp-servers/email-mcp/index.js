#!/usr/bin/env node

/**
 * Email MCP Server
 * 
 * Provides email capabilities via Gmail API through MCP protocol.
 * Tools: send_email, get_profile, reply_to_email
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

import { google } from 'googleapis';

const server = new Server(
  {
    name: 'email-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

let gmailService = null;

/**
 * Initialize Gmail API service
 */
async function initializeGmail() {
  try {
    const tokenString = process.env.GMAIL_TOKEN;
    if (!tokenString) {
      console.error('GMAIL_TOKEN environment variable not set');
      return false;
    }

    const tokenData = JSON.parse(tokenString);
    // Ensure access_token is set (it might be in 'token' field)
    if (tokenData.token && !tokenData.access_token) {
      tokenData.access_token = tokenData.token;
    }

    const oauth2Client = new google.auth.OAuth2();
    oauth2Client.setCredentials(tokenData);

    gmailService = google.gmail({ version: 'v1', auth: oauth2Client });
    console.error('Gmail service initialized successfully');
    return true;
  } catch (error) {
    console.error('Failed to initialize Gmail service:', error);
    return false;
  }
}

// Tool definitions
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'send_email',
        description: 'Send an email via Gmail',
        inputSchema: {
          type: 'object',
          properties: {
            to: {
              type: 'string',
              description: 'Recipient email address',
            },
            subject: {
              type: 'string',
              description: 'Email subject line',
            },
            body: {
              type: 'string',
              description: 'Email body content',
            },
            is_html: {
              type: 'boolean',
              description: 'Whether the body contains HTML (default: false)',
            },
          },
          required: ['to', 'subject', 'body'],
        },
      },
      {
        name: 'get_profile',
        description: 'Get the authenticated user\'s Gmail profile',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
      {
        name: 'reply_to_email',
        description: 'Reply to an existing email conversation',
        inputSchema: {
          type: 'object',
          properties: {
            threadId: {
              type: 'string',
              description: 'The ID of the thread to reply to',
            },
            messageId: {
              type: 'string',
              description: 'The ID of the specific message being replied to (for In-Reply-To header)',
            },
            to: {
              type: 'string',
              description: 'Recipient email address',
            },
            body: {
              type: 'string',
              description: 'Reply body content',
            },
            is_html: {
              type: 'boolean',
              description: 'Whether the body contains HTML (default: false)',
            },
          },
          required: ['threadId', 'messageId', 'to', 'body'],
        },
      },
    ],
  };
});

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (!gmailService) {
    const initialized = await initializeGmail();
    if (!initialized) {
      throw new Error('Failed to initialize Gmail service. Check GMAIL_TOKEN.');
    }
  }

  try {
    switch (name) {
      case 'send_email': {
        const { to, subject, body, is_html = false } = args;

        if (!to || !subject || !body) {
          throw new Error('Missing required parameters: to, subject, body');
        }

        // Manual MIME construction with CRLF and basic headers
        const str = [
          `To: ${to}`,
          `Subject: ${subject}`,
          'MIME-Version: 1.0',
          `Content-Type: ${is_html ? 'text/html' : 'text/plain'}; charset=utf-8`,
          'Content-Transfer-Encoding: 7bit',
          '',
          body
        ].join('\r\n');

        const rawMessage = Buffer.from(str)
          .toString('base64')
          .replace(/\+/g, '-')
          .replace(/\//g, '_')
          .replace(/=+$/, '');

        const response = await gmailService.users.messages.send({
          userId: 'me',
          requestBody: {
            raw: rawMessage,
          },
        });

        return {
          content: [
            {
              type: 'text',
              text: `Email sent successfully! Message ID: ${response.data.id}`,
            },
          ],
        };
      }

      case 'get_profile': {
        const profile = await gmailService.users.getProfile({
          userId: 'me',
        });

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                email_address: profile.data.emailAddress,
                messages_total: profile.data.messagesTotal,
                threads_total: profile.data.threadsTotal,
                history_id: profile.data.historyId,
              }, null, 2),
            },
          ],
        };
      }

      case 'reply_to_email': {
        const { threadId, messageId, to, body, is_html = false } = args;

        if (!threadId || !messageId || !to || !body) {
          throw new Error('Missing required arguments');
        }

        // Manual MIME construction with CRLF
        const str = [
          `To: ${to}`,
          'MIME-Version: 1.0',
          `Content-Type: ${is_html ? 'text/html' : 'text/plain'}; charset=utf-8`,
          'Content-Transfer-Encoding: 7bit',
          `In-Reply-To: ${messageId}`,
          `References: ${messageId}`,
          '',
          body
        ].join('\r\n');

        const rawMessage = Buffer.from(str)
          .toString('base64')
          .replace(/\+/g, '-')
          .replace(/\//g, '_')
          .replace(/=+$/, '');

        const response = await gmailService.users.messages.send({
          userId: 'me',
          requestBody: {
            raw: rawMessage,
            threadId: threadId
          },
        });

        return {
          content: [
            {
              type: 'text',
              text: `Reply sent successfully! New Message ID: ${response.data.id} in Thread: ${response.data.threadId}`,
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

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Email MCP server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error in main():', error);
  process.exit(1);
});
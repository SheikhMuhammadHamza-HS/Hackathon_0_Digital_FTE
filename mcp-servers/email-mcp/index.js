#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { google } from 'googleapis';

// Initialize Gmail API
let gmailService = null;

async function initializeGmail() {
  const token = process.env.GMAIL_TOKEN;
  if (!token) {
    console.error('GMAIL_TOKEN environment variable not set');
    return false;
  }

  try {
    const credentials = JSON.parse(token);
    const { OAuth2 } = google.auth;
    const oauth2Client = new OAuth2(
      credentials.client_id,
      credentials.client_secret,
      credentials.redirect_uri
    );
    oauth2Client.setCredentials({
      access_token: credentials.access_token,
      refresh_token: credentials.refresh_token,
      expiry_date: credentials.expiry_date
    });

    gmailService = google.gmail({ version: 'v1', auth: oauth2Client });
    return true;
  } catch (error) {
    console.error('Failed to initialize Gmail:', error.message);
    return false;
  }
}

// Create MCP Server
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

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'send_email',
        description: 'Send an email via Gmail API',
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
              description: 'Email body content (plain text or HTML)',
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

        const { default: email } = await import('emailjs-mime-builder');
        const message = new email();

        message.setSubject(subject);
        message.setTo(to);
        message.setTextBody(body);

        if (is_html) {
          message.setHtmlBody(body);
        }

        const rawMessage = Buffer.from(message.build()).toString('base64');

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
  console.error('Email MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
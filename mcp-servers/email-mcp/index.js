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

    // Initialize with client ID and secret for refresh capability
    const oauth2Client = new google.auth.OAuth2(
      tokenData.client_id,
      tokenData.client_secret
    );

    // Map fields for google-auth-library compatibility
    oauth2Client.setCredentials({
      access_token: tokenData.token || tokenData.access_token,
      refresh_token: tokenData.refresh_token,
      expiry_date: tokenData.expiry ? new Date(tokenData.expiry).getTime() : null,
      scope: tokenData.scopes?.join(' ')
    });

    gmailService = google.gmail({ version: 'v1', auth: oauth2Client });
    console.error('Gmail service initialized successfully (Token refresh enabled)');
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
            subject: {
              type: 'string',
              description: 'Optional subject line',
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

        // Normalize all line endings in body to \r\n to comply with rfc2822
        const normalizedBody = body.replace(/\r?\n/g, '\r\n');

        // Manual MIME construction with CRLF
        const str = [
          `To: ${to}`,
          `Subject: ${subject}`,
          'MIME-Version: 1.0',
          `Content-Type: text/plain; charset=utf-8`,
          '',
          normalizedBody
        ].join('\r\n');

        console.error('Constructed MIME message for debugging:');
        console.error('-------------------------------------------');
        console.error(str);
        console.error('-------------------------------------------');

        const rawMessage = Buffer.from(str)
          .toString('base64')
          .replace(/\+/g, '-')
          .replace(/\//g, '_')
          .replace(/=+$/, '');

        try {
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
        } catch (apiError) {
          console.error('Gmail API Error Details:', JSON.stringify(apiError.response?.data || apiError, null, 2));
          throw apiError;
        }
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
        const { threadId, messageId, to, subject, body, is_html = false } = args;

        if (!threadId || !to || !body) {
          throw new Error('Missing required arguments: threadId, to, body');
        }

        const normalizedBody = body.replace(/\r?\n/g, '\r\n');

        // Extreme simplification: Just To, Subject, and Body
        // Threading is handled by threadId in the requestBody
        const headers = [
          `To: ${to}`,
          `Subject: ${subject || 'Re: (No Subject)'}`,
          'MIME-Version: 1.0',
          `Content-Type: text/plain; charset=utf-8`
        ];

        const str = [
          ...headers,
          '',
          normalizedBody
        ].join('\r\n');

        const rawMessage = Buffer.from(str)
          .toString('base64')
          .replace(/\+/g, '-')
          .replace(/\//g, '_')
          .replace(/=+$/, '');

        try {
          const response = await gmailService.users.messages.send({
            userId: 'me',
            requestBody: {
              raw: rawMessage,
              threadId: threadId
            },
          });

          return {
            content: [{
              type: 'text',
              text: `Reply sent successfully! ID: ${response.data.id}`,
            }],
          };
        } catch (apiError) {
          const detail = apiError.response?.data?.error?.message || apiError.message;
          return {
            content: [{
              type: 'text',
              text: `Error executing reply_to_email: ${detail}`,
            }],
            isError: true,
          };
        }
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
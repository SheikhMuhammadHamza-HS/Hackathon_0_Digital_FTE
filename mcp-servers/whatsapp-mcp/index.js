#!/usr/bin/env node

/**
 * WhatsApp MCP Server
 * 
 * Provides WhatsApp capabilities via WhatsApp Business API.
 * Tools: send_message, send_template
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
    ListToolsRequestSchema,
    CallToolRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

import axios from 'axios';

const server = new Server(
    {
        name: 'whatsapp-mcp',
        version: '1.0.0',
    },
    {
        capabilities: {
            tools: {},
        },
    }
);

const API_VERSION = 'v21.0';
const FACEBOOK_API_URL = 'https://graph.facebook.com';

/**
 * Handle sending WhatsApp messages
 */
async function sendMessage(to, body, phoneNumberId, accessToken) {
    try {
        const url = `${FACEBOOK_API_URL}/${API_VERSION}/${phoneNumberId}/messages`;
        const response = await axios.post(
            url,
            {
                messaging_product: 'whatsapp',
                recipient_type: 'individual',
                to: to.replace(/\+/g, '').replace(/\s/g, ''), // E.164 format without +
                type: 'text',
                text: {
                    preview_url: false,
                    body: body,
                },
            },
            {
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json',
                },
            }
        );
        return response.data;
    } catch (error) {
        const errorData = error.response ? error.response.data : error.message;
        console.error('WhatsApp API Error:', JSON.stringify(errorData));
        throw new Error(`WhatsApp API Error: ${JSON.stringify(errorData)}`);
    }
}

/**
 * Handle sending WhatsApp template messages
 */
async function sendTemplate(to, templateName, languageCode, phoneNumberId, accessToken) {
    try {
        const url = `${FACEBOOK_API_URL}/${API_VERSION}/${phoneNumberId}/messages`;
        const response = await axios.post(
            url,
            {
                messaging_product: 'whatsapp',
                recipient_type: 'individual',
                to: to.replace(/\+/g, '').replace(/\s/g, ''),
                type: 'template',
                template: {
                    name: templateName,
                    language: {
                        code: languageCode || 'en_US',
                    },
                },
            },
            {
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json',
                },
            }
        );
        return response.data;
    } catch (error) {
        const errorData = error.response ? error.response.data : error.message;
        console.error('WhatsApp API Error:', JSON.stringify(errorData));
        throw new Error(`WhatsApp API Error: ${JSON.stringify(errorData)}`);
    }
}

// Tool definitions
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: 'send_message',
                description: 'Send a text message via WhatsApp Business API',
                inputSchema: {
                    type: 'object',
                    properties: {
                        to: {
                            type: 'string',
                            description: 'Recipient phone number in international format (e.g., +14155551234)',
                        },
                        body: {
                            type: 'string',
                            description: 'Message body content',
                        },
                        phone_number_id: {
                            type: 'string',
                            description: 'Business phone number ID (optional, defaults to env var)',
                        },
                    },
                    required: ['to', 'body'],
                },
            },
            {
                name: 'send_template',
                description: 'Send a template message via WhatsApp Business API',
                inputSchema: {
                    type: 'object',
                    properties: {
                        to: {
                            type: 'string',
                            description: 'Recipient phone number',
                        },
                        template_name: {
                            type: 'string',
                            description: 'Name of the template (e.g., hello_world)',
                        },
                        language_code: {
                            type: 'string',
                            description: 'Language code (default: en_US)',
                        },
                    },
                    required: ['to', 'template_name'],
                },
            },
        ],
    };
});

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    const PHONE_NUMBER_ID = args.phone_number_id || process.env.WHATSAPP_PHONE_NUMBER_ID;
    const ACCESS_TOKEN = process.env.WHATSAPP_ACCESS_TOKEN;

    if (!PHONE_NUMBER_ID || !ACCESS_TOKEN) {
        throw new Error('Missing WhatsApp configuration: WHATSAPP_PHONE_NUMBER_ID or WHATSAPP_ACCESS_TOKEN');
    }

    try {
        switch (name) {
            case 'send_message': {
                const { to, body } = args;
                const result = await sendMessage(to, body, PHONE_NUMBER_ID, ACCESS_TOKEN);
                return {
                    content: [
                        {
                            type: 'text',
                            text: `WhatsApp message sent successfully! ID: ${result.messages[0].id}`,
                        },
                    ],
                };
            }
            case 'send_template': {
                const { to, template_name, language_code } = args;
                const result = await sendTemplate(to, template_name, language_code, PHONE_NUMBER_ID, ACCESS_TOKEN);
                return {
                    content: [
                        {
                            type: 'text',
                            text: `WhatsApp template sent successfully! ID: ${result.messages[0].id}`,
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
                    text: `Error: ${error.message}`,
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
    console.error('WhatsApp MCP server running on stdio');
}

main().catch((error) => {
    console.error('Fatal error in main():', error);
    process.exit(1);
});

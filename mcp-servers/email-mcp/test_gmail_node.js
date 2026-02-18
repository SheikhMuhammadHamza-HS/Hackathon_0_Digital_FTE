import { google } from 'googleapis';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function test() {
    const tokenPath = path.join(__dirname, '..', '..', 'token.json');
    const token = fs.readFileSync(tokenPath, 'utf8');
    if (!token) {
        console.error('token.json not found');
        return;
    }

    const credentials = JSON.parse(token);
    const auth = new google.auth.OAuth2(
        credentials.client_id,
        credentials.client_secret
    );
    auth.setCredentials({
        access_token: credentials.token,
        refresh_token: credentials.refresh_token,
        expiry_date: new Date(credentials.expiry).getTime()
    });

    const gmail = google.gmail({ version: 'v1', auth });

    const to = 'sheikhasadullah22@gmail.com';
    const subject = 'Test from Node.js';
    const body = 'Hello from Node.js script';
    const threadId = '19c708f72f09095e';

    const str = [
        `To: ${to}`,
        `Subject: ${subject}`,
        'MIME-Version: 1.0',
        `Content-Type: text/plain; charset=utf-8`,
        '',
        body
    ].join('\r\n');

    const raw = Buffer.from(str)
        .toString('base64')
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '');

    try {
        const res = await gmail.users.messages.send({
            userId: 'me',
            requestBody: {
                raw: raw,
                threadId: threadId
            }
        });
        console.log('Success!', res.data.id);
    } catch (err) {
        console.error('Error:', err.response ? err.response.data : err.message);
    }
}

test();

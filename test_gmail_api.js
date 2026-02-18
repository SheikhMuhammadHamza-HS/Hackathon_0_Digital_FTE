const { google } = require('googleapis');
const dotenv = require('dotenv');
dotenv.config();

async function testSend() {
    const tokenString = process.env.GMAIL_TOKEN;
    if (!tokenString) {
        console.error('GMAIL_TOKEN not set');
        return;
    }

    const tokenData = JSON.parse(tokenString);
    if (tokenData.token && !tokenData.access_token) {
        tokenData.access_token = tokenData.token;
    }

    const oauth2Client = new google.auth.OAuth2();
    oauth2Client.setCredentials(tokenData);
    const gmail = google.gmail({ version: 'v1', auth: oauth2Client });

    const to = 'sheikhasadullah22@gmail.com';
    const subject = 'Test from Agent';
    const body = 'This is a test message to debug invalid_request.';

    const str = [
        `From: me`,
        `To: ${to}`,
        `Subject: ${subject}`,
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=utf-8',
        '',
        body
    ].join('\r\n');

    const raw = Buffer.from(str).toString('base64url');

    try {
        const res = await gmail.users.messages.send({
            userId: 'me',
            requestBody: { raw }
        });
        console.log('Success!', res.data);
    } catch (e) {
        console.error('Error:', e.response?.data || e.message);
    }
}

testSend();

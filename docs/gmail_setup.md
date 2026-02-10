# Gmail OAuth Setup Guide

To enable real Gmail automation, you need to provide OAuth2 credentials to the Agent.

## Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project.
3. Enable the **Gmail API**.

## Step 2: Configure OAuth Consent Screen
1. Go to "APIs & Services" > "OAuth consent screen".
2. Select "External" (or Internal if you have a Google Workspace).
3. Add your email to "Test users".
4. Add the scope: `https://www.googleapis.com/auth/gmail.modify`.

## Step 3: Create Credentials
1. Go to "APIs & Services" > "Credentials".
2. Click "Create Credentials" > "OAuth client ID".
3. Select "Desktop app".
4. Download the `client_secret_XXXX.json` file.
5. Rename it to `credentials.json` and place it in the project root.

## Step 4: Generate Token
1. Run the following command (you may need to install `google-auth-oauthlib`):
   ```bash
   pip install google-auth-oauthlib google-auth-httplib2
   ```
2. You can use a small script to generate the `token.json`. 
   (The Agent will look for `token.json` in the root or a `GMAIL_TOKEN` string in `.env`).

## Step 5: Configure Agent
Once you have `token.json`, you can either:
- Leave it as `token.json` in the project root.
- OR: Copy the JSON content and set it as `GMAIL_TOKEN` in your `.env` file.

```env
GMAIL_TOKEN='{"token": "...", "refresh_token": "...", ...}'
```

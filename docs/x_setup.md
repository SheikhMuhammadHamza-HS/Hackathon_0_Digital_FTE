# X (Twitter) API Setup Guide 🐦

Follow these steps to get your credentials for the Digital FTE Agent.

### 1. Developer Account Shuru Karein
1. [X Developer Portal](https://developer.x.com/en/portal/dashboard) par jayein.
2. Apne X account se login karein.
3. Agar pucha jaye to **"Sign up for a Free Account"** (ya Basic) select karein.
4. Apni use case (Description) mein likhein: *"Personal AI agent for automating my own social media posts and scheduling tweets."*

### 2. Project aur App Banayein
1. Dashboard par **"Create Project"** par click karein.
2. Project ka naam rakhein (e.g., `DigitalFTEAgent`).
3. App ka naam rakhein (e.g., `MyFTEBot`).

### 3. User Authentication Settings (ZAROORI)
1. Apni App ki **Settings** (Gear icon) mein jayein.
2. **"User authentication settings"** par click karein aur **"Set up"** dabayein.
3. **App Permissions**: `Read and Write` select karein.
4. **Type of App**: `Web App, Automated App or Bot` select karein.
5. **App Info**:
   - `Callback URI / Redirect URL`: `http://localhost:8080` (Aap koi bhi valid URL dal sakte hain).
   - `Website URL`: Aapka GitHub link ya koi bhi personal URL.
6. **Save** dabayein.

### 4. Keys aur Tokens Hasil Karein
1. **"Keys and Tokens"** tab par jayein.
2. **Consumer Keys**:
   - `API Key` aur `API Secret` ko "Regenerate" ya "View" karke copy karein.
3. **Authentication Tokens**:
   - `Access Token` aur `Access Token Secret` ko "Generate" karein (Dhyan rahe ke permissions **Created with Read and Write** honi chahiyen).

### 5. .env Mein Add Karein
Ye sab copy karke apni `.env` file mein dal dein:

```env
X_API_KEY=your_api_key_here
X_API_SECRET=your_api_secret_here
X_ACCESS_TOKEN=your_access_token_here
X_ACCESS_SECRET=your_access_secret_here
```

# 𝕏 (Twitter) Real API Setup Guide

To fulfill the **Platinum Tier** requirement for "Twitter/X Real API", follow these steps to replace the Playwright automation with official API calls.

## 1. Create X Developer Account
1. Go to [developer.x.com](https://developer.x.com).
2. Create a new App in the Developer Portal.
3. **Crucial:** Set "User authentication settings" to:
   - **App permissions:** Read and Write.
   - **Type of App:** Web App, Native App, or Carousel.
   - **Callback URI:** `http://localhost:8000` (or your domain).
   - **Website URL:** Your website or GitHub profile.

## 2. Get Your Keys
You need 4 specific strings from the "Keys and Tokens" tab:
1. `API Key` (Consumer Key)
2. `API Key Secret` (Consumer Secret)
3. `Access Token`
4. `Access Token Secret`

## 3. Update `.env`
Update your `.env` file with the real keys:

```env
X_API_KEY=your_real_key_here
X_API_SECRET=your_real_secret_here
X_ACCESS_TOKEN=your_real_token_here
X_ACCESS_SECRET=your_real_token_secret_here
```

## 4. Verification
Run the verification script:
```bash
python scripts/x/verify_x_integration.py
```

If these keys are present, the system will automatically use `tweepy` (X API v2) instead of opening a browser window.

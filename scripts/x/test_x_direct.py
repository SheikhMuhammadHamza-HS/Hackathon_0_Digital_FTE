import os
import tweepy
from dotenv import load_dotenv

def test_x_connection():
    load_dotenv()
    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_secret = os.getenv("X_ACCESS_SECRET")

    print(f"Testing X API v2 with:")
    print(f"API Key: {api_key[:5]}...{api_key[-5:] if api_key else ''}")
    print(f"Access Token: {access_token[:5]}...{access_token[-5:] if access_token else ''}")

    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret
        )
        print("Attempting to post a diagnostic tweet...")
        response = client.create_tweet(text="Diagnostic tweet from Digital FTE Agent Setup! #XAPI #Python")
        print(f"SUCCESS! Tweet ID: {response.data['id']}")
    except Exception as e:
        print(f"FAILURE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_x_connection()

import requests
import time

def check_render_api():
    url = "https://hackathon-0-digital-fte.onrender.com/api/v1/approvals"
    print(f"🌐 Fetching approvals from Render: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            print(f"✅ Success! Total approvals found: {total}")
            if total > 0:
                for app in data.get('approvals', []):
                    print(f"   - Subject: {app.get('subject')}")
            else:
                print("   (List is empty)")
                if 'checked_paths' in data:
                    print(f"   Debug Info - Paths checked: {data['checked_paths']}")
                if 'location' in data:
                    print(f"   Debug Info - Last location: {data['location']}")
        else:
            print(f"❌ Failed with status code: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    check_render_api()

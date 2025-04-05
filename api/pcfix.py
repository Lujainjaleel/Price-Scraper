import requests
import base64
import json

# Replace with your app's key and secret
APP_KEY = "bcvvobmq9urp9b3"
APP_SECRET = "bq3ggjy0v47iymw"

# Step 1: Get authorization URL
auth_url = f"https://www.dropbox.com/oauth2/authorize?client_id={APP_KEY}&response_type=code&token_access_type=offline"
print(f"1. Go to this URL in your browser: {auth_url}")
print("2. Click 'Allow' (you might have to log in first)")
print("3. Copy the authorization code")

# Step 2: Get the authorization code from user
auth_code = input("Enter the authorization code: ").strip()

# Step 3: Exchange auth code for tokens
token_url = "https://api.dropboxapi.com/oauth2/token"
auth_header = base64.b64encode(f"{APP_KEY}:{APP_SECRET}".encode()).decode()

headers = {
    "Authorization": f"Basic {auth_header}",
    "Content-Type": "application/x-www-form-urlencoded"
}

data = {
    "code": auth_code,
    "grant_type": "authorization_code"
}

response = requests.post(token_url, headers=headers, data=data)
if response.status_code == 200:
    token_data = response.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    
    print(f"Access Token: {access_token}")
    print(f"Refresh Token: {refresh_token}")
    
    # Save these tokens to use in your application
    print("\nAdd these to your app.py file:")
    print(f"DROPBOX_APP_KEY = \"{APP_KEY}\"")
    print(f"DROPBOX_APP_SECRET = \"{APP_SECRET}\"")
    print(f"DROPBOX_REFRESH_TOKEN = \"{refresh_token}\"")
    print(f"DROPBOX_ACCESS_TOKEN = \"{access_token}\"")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
import requests
from django.conf import settings

def get_dropbox_access_token():
    url = "https://api.dropbox.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": settings.DROPBOX_REFRESH_TOKEN,
        "client_id": settings.DROPBOX_APP_KEY,
        "client_secret": settings.DROPBOX_APP_SECRET,
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"] 
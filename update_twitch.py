import requests
import os

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "ВАШ_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "ВАШ_CLIENT_SECRET")
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN", "ВАШ_OAUTH_TOKEN")
TWITCH_REFRESH_TOKEN = os.getenv("TWITCH_REFRESH_TOKEN", "ВАШ_REFRESH_TOKEN")
TWITCH_BROADCASTER_ID = os.getenv("TWITCH_BROADCASTER_ID", "ВАШ_ID_КАНАЛА")

def refresh_twitch_token():
    """Обновляет токен Twitch с помощью refresh token"""
    try:
        url = "https://id.twitch.tv/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": TWITCH_REFRESH_TOKEN,
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET
        }
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
        token_data = r.json()
        global TWITCH_TOKEN, TWITCH_REFRESH_TOKEN
        TWITCH_TOKEN = token_data["access_token"]
        if "refresh_token" in token_data:
            TWITCH_REFRESH_TOKEN = token_data["refresh_token"]
        # Обновляем переменные окружения
        os.environ["TWITCH_TOKEN"] = TWITCH_TOKEN
        if "refresh_token" in token_data:
            os.environ["TWITCH_REFRESH_TOKEN"] = TWITCH_REFRESH_TOKEN
        print("[TWITCH] Token refreshed successfully")
        return True
    except Exception as e:
        print(f"[TWITCH] Failed to refresh token: {e}")
        return False

def make_twitch_request(method, url, headers=None, params=None, json=None, timeout=5):
    """Делает запрос к Twitch API с автоматическим рефрешем токена при 401"""
    if headers is None:
        headers = {}
    if "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {TWITCH_TOKEN}"
    if "Client-ID" not in headers:
        headers["Client-ID"] = TWITCH_CLIENT_ID

    r = requests.request(method, url, headers=headers, params=params, json=json, timeout=timeout)

    # Если 401 Unauthorized, пытаемся рефрешить токен и повторить запрос
    if r.status_code == 401:
        if refresh_twitch_token():
            headers["Authorization"] = f"Bearer {TWITCH_TOKEN}"
            r = requests.request(method, url, headers=headers, params=params, json=json, timeout=timeout)

    return r

def get_game_id(category_name):
    if not category_name:
        return None
    url = "https://api.twitch.tv/helix/games"
    params = {"name": category_name}
    r = make_twitch_request("GET", url, params=params)
    r.raise_for_status()
    data = r.json().get("data", [])
    if not data:
        return None
    return data[0]["id"]

def update_twitch(title, category):
    game_id = get_game_id(category)
    url = "https://api.twitch.tv/helix/channels"
    params = {"broadcaster_id": TWITCH_BROADCASTER_ID}
    headers = {"Content-Type": "application/json"}
    body = {"title": title}
    if game_id:
        body["game_id"] = game_id
    r = make_twitch_request("PATCH", url, headers=headers, params=params, json=body)
    r.raise_for_status()

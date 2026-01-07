import requests

TWITCH_CLIENT_ID = "ВАШ_CLIENT_ID"
TWITCH_TOKEN = "ВАШ_OAUTH_TOKEN"
TWITCH_BROADCASTER_ID = "ВАШ_ID_КАНАЛА"

def get_game_id(category_name):
    if not category_name:
        return None
    url = "https://api.twitch.tv/helix/games"
    params = {"name": category_name}
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {TWITCH_TOKEN}"
    }
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    data = r.json().get("data", [])
    if not data:
        return None
    return data[0]["id"]

def update_twitch(title, category):
    game_id = get_game_id(category)
    url = "https://api.twitch.tv/helix/channels"
    params = {"broadcaster_id": TWITCH_BROADCASTER_ID}
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {TWITCH_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {"title": title}
    if game_id:
        body["game_id"] = game_id
    r = requests.patch(url, params=params, headers=headers, json=body)
    r.raise_for_status()

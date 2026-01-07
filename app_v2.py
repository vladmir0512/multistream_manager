"""
Stream Manager for OBS Studio
Управление названием и категорией стрима на нескольких платформах одновременно

Поддерживаемые платформы: Twitch, YouTube, Trovo, VK Play Live, Kick
"""

from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime
import requests
from typing import Optional, Dict, List

# Загрузить переменные из .env если используется python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

# ==================== КОНФИГУРАЦИЯ ====================

TWITCH_CONFIG = {
    "client_id": os.getenv("TWITCH_CLIENT_ID", ""),
    "client_secret": os.getenv("TWITCH_CLIENT_SECRET", ""),
    "access_token": os.getenv("TWITCH_TOKEN", ""),
    "refresh_token": os.getenv("TWITCH_REFRESH_TOKEN", ""),
    "broadcaster_id": os.getenv("TWITCH_BROADCASTER_ID", ""),
}

def refresh_twitch_token() -> bool:
    """Обновляет токен Twitch с помощью refresh token"""
    try:
        url = "https://id.twitch.tv/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": TWITCH_CONFIG["refresh_token"],
            "client_id": TWITCH_CONFIG["client_id"],
            "client_secret": TWITCH_CONFIG["client_secret"]
        }
        resp = requests.post(url, data=data, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()

        TWITCH_CONFIG["access_token"] = token_data["access_token"]
        if "refresh_token" in token_data:
            TWITCH_CONFIG["refresh_token"] = token_data["refresh_token"]

        # Обновляем переменные окружения, если возможно
        os.environ["TWITCH_TOKEN"] = TWITCH_CONFIG["access_token"]
        if "refresh_token" in token_data:
            os.environ["TWITCH_REFRESH_TOKEN"] = TWITCH_CONFIG["refresh_token"]

        print("[TWITCH] Token refreshed successfully")
        return True
    except Exception as e:
        print(f"[TWITCH] Failed to refresh token: {e}")
        return False

def make_twitch_request(method: str, url: str, headers: Dict = None, params: Dict = None, json: Dict = None, timeout: int = 5) -> requests.Response:
    """Делает запрос к Twitch API с автоматическим рефрешем токена при 401"""
    if headers is None:
        headers = {}
    if "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {TWITCH_CONFIG['access_token']}"
    if "Client-ID" not in headers:
        headers["Client-ID"] = TWITCH_CONFIG["client_id"]

    resp = requests.request(method, url, headers=headers, params=params, json=json, timeout=timeout)

    # Если 401 Unauthorized, пытаемся рефрешить токен и повторить запрос
    if resp.status_code == 401:
        if refresh_twitch_token():
            # Обновляем заголовок с новым токеном
            headers["Authorization"] = f"Bearer {TWITCH_CONFIG['access_token']}"
            resp = requests.request(method, url, headers=headers, params=params, json=json, timeout=timeout)

    return resp

YOUTUBE_CONFIG = {
    "client_id": os.getenv("YOUTUBE_CLIENT_ID", ""),
    "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET", ""),
    "access_token": os.getenv("YOUTUBE_TOKEN", ""),
    "refresh_token": os.getenv("YOUTUBE_REFRESH_TOKEN", ""),
    "video_id": os.getenv("YOUTUBE_VIDEO_ID", ""),
}

def refresh_youtube_token() -> bool:
    """Обновляет токен YouTube с помощью refresh token"""
    try:
        url = "https://oauth2.googleapis.com/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": YOUTUBE_CONFIG["refresh_token"],
            "client_id": YOUTUBE_CONFIG["client_id"],
            "client_secret": YOUTUBE_CONFIG["client_secret"]
        }
        resp = requests.post(url, data=data, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()

        YOUTUBE_CONFIG["access_token"] = token_data["access_token"]
        # YouTube может вернуть новый refresh_token
        if "refresh_token" in token_data:
            YOUTUBE_CONFIG["refresh_token"] = token_data["refresh_token"]

        # Обновляем переменные окружения
        os.environ["YOUTUBE_TOKEN"] = YOUTUBE_CONFIG["access_token"]
        if "refresh_token" in token_data:
            os.environ["YOUTUBE_REFRESH_TOKEN"] = YOUTUBE_CONFIG["refresh_token"]

        print("[YOUTUBE] Token refreshed successfully")
        return True
    except Exception as e:
        print(f"[YOUTUBE] Failed to refresh token: {e}")
        return False

def make_youtube_request(method: str, url: str, headers: Dict = None, params: Dict = None, json: Dict = None, timeout: int = 5) -> requests.Response:
    """Делает запрос к YouTube API с автоматическим рефрешем токена при 401"""
    if headers is None:
        headers = {}
    if "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {YOUTUBE_CONFIG['access_token']}"

    resp = requests.request(method, url, headers=headers, params=params, json=json, timeout=timeout)

    # Если 401 Unauthorized, пытаемся рефрешить токен и повторить запрос
    if resp.status_code == 401:
        if refresh_youtube_token():
            # Обновляем заголовок с новым токеном
            headers["Authorization"] = f"Bearer {YOUTUBE_CONFIG['access_token']}"
            resp = requests.request(method, url, headers=headers, params=params, json=json, timeout=timeout)

    return resp

TROVO_CONFIG = {
    "client_id": os.getenv("TROVO_CLIENT_ID", ""),
    "client_secret": os.getenv("TROVO_CLIENT_SECRET", ""),
    "access_token": os.getenv("TROVO_TOKEN", ""),
    "refresh_token": os.getenv("TROVO_REFRESH_TOKEN", ""),
    "channel_id": os.getenv("TROVO_CHANNEL_ID", ""),
}

def refresh_trovo_token() -> bool:
    """Обновляет токен Trovo с помощью refresh token"""
    try:
        url = "https://open-api.trovo.live/openplatform/refreshtoken"
        data = {
            "grant_type": "refresh_token",
            "client_id": TROVO_CONFIG["client_id"],
            "client_secret": TROVO_CONFIG["client_secret"],
            "refresh_token": TROVO_CONFIG["refresh_token"]
        }
        resp = requests.post(url, data=data, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()

        TROVO_CONFIG["access_token"] = token_data["access_token"]
        if "refresh_token" in token_data:
            TROVO_CONFIG["refresh_token"] = token_data["refresh_token"]

        # Обновляем переменные окружения
        os.environ["TROVO_TOKEN"] = TROVO_CONFIG["access_token"]
        if "refresh_token" in token_data:
            os.environ["TROVO_REFRESH_TOKEN"] = TROVO_CONFIG["refresh_token"]

        print("[TROVO] Token refreshed successfully")
        return True
    except Exception as e:
        print(f"[TROVO] Failed to refresh token: {e}")
        return False

def make_trovo_request(method: str, url: str, headers: Dict = None, params: Dict = None, json: Dict = None, timeout: int = 5) -> requests.Response:
    """Делает запрос к Trovo API с автоматическим рефрешем токена при 401"""
    if headers is None:
        headers = {}
    if "Client-ID" not in headers:
        headers["Client-ID"] = TROVO_CONFIG["client_id"]
    if "Authorization" not in headers:
        headers["Authorization"] = f"OAuth {TROVO_CONFIG['access_token']}"

    resp = requests.request(method, url, headers=headers, params=params, json=json, timeout=timeout)

    # Если 401 Unauthorized, пытаемся рефрешить токен и повторить запрос
    if resp.status_code == 401:
        if refresh_trovo_token():
            # Обновляем заголовок с новым токеном
            headers["Authorization"] = f"OAuth {TROVO_CONFIG['access_token']}"
            resp = requests.request(method, url, headers=headers, params=params, json=json, timeout=timeout)

    return resp

VKPLAY_CONFIG = {
    "access_token": os.getenv("VKPLAY_TOKEN", ""),
    "channel_id": os.getenv("VKPLAY_CHANNEL_ID", ""),
}

KICK_CONFIG = {
    "access_token": os.getenv("KICK_TOKEN", ""),
    "channel_slug": os.getenv("KICK_CHANNEL_SLUG", ""),
}

HISTORY_FILE = "stream_history.json"
MAX_HISTORY = 10

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def load_history() -> List[Dict]:
    """Загружает историю из файла"""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[HISTORY] Error loading: {e}")
        return []

def save_history(history: List[Dict]) -> None:
    """Сохраняет историю в файл"""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[HISTORY] Error saving: {e}")

def add_to_history(title: str, category: str) -> None:
    """Добавляет запись в историю"""
    history = load_history()
    entry = {
        "title": title,
        "category": category,
        "timestamp": datetime.now().isoformat(timespec="seconds")
    }
    history = [h for h in history if not (h["title"] == title and h["category"] == category)]
    history.insert(0, entry)
    history = history[:MAX_HISTORY]
    save_history(history)

def check_config() -> Dict[str, bool]:
    """Проверяет, какие конфиги заполнены"""
    return {
        "twitch": bool(TWITCH_CONFIG["access_token"]),
        "youtube": bool(YOUTUBE_CONFIG["access_token"]),
        "trovo": bool(TROVO_CONFIG["access_token"]),
        "vkplay": bool(VKPLAY_CONFIG["access_token"]),
        "kick": bool(KICK_CONFIG["access_token"]),
    }

# ==================== TWITCH ====================

def get_twitch_game_id(game_name: str) -> Optional[str]:
    """Получает ID игры в Twitch по названию"""
    if not game_name:
        return None

    if not TWITCH_CONFIG["access_token"]:
        print("[TWITCH] Missing access_token")
        return None

    url = "https://api.twitch.tv/helix/games"
    params = {"name": game_name}

    try:
        resp = make_twitch_request("GET", url, params=params)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if data:
            game_id = data[0]["id"]
            print(f"[TWITCH] Found game ID: {game_id} for '{game_name}'")
            return game_id
        else:
            print(f"[TWITCH] Game '{game_name}' not found")
    except requests.exceptions.HTTPError as e:
        print(f"[TWITCH] HTTP Error getting game ID: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"[TWITCH] Error getting game ID: {e}")

    return None

def update_twitch(title: str, category: str) -> Dict:
    """Обновляет название и категорию на Twitch"""
    try:
        if not TWITCH_CONFIG["access_token"]:
            return {"success": False, "error": "Twitch token не настроен"}

        if not TWITCH_CONFIG["broadcaster_id"]:
            return {"success": False, "error": "Twitch broadcaster_id не настроен"}

        game_id = get_twitch_game_id(category) if category else None

        url = "https://api.twitch.tv/helix/channels"
        headers = {"Content-Type": "application/json"}
        params = {"broadcaster_id": TWITCH_CONFIG["broadcaster_id"]}

        body = {"title": title}
        if game_id:
            body["game_id"] = game_id

        print(f"[TWITCH] Updating: title='{title}', game_id={game_id}")

        resp = make_twitch_request("PATCH", url, headers=headers, params=params, json=body)
        resp.raise_for_status()

        print(f"[TWITCH] ✅ Success")
        return {"success": True, "message": "Twitch обновлен"}
    except Exception as e:
        error_msg = str(e)
        print(f"[TWITCH] ❌ Error: {error_msg}")
        return {"success": False, "error": f"Twitch: {error_msg}"}

# ==================== YOUTUBE ====================

def update_youtube(title: str, category: str) -> Dict:
    """Обновляет название на YouTube"""
    try:
        if not YOUTUBE_CONFIG["access_token"]:
            return {"success": False, "error": "YouTube token не настроен"}

        if not YOUTUBE_CONFIG["video_id"]:
            return {"success": False, "error": "YouTube video_id не настроен"}

        url_put = "https://www.googleapis.com/youtube/v3/videos"
        headers = {"Content-Type": "application/json"}
        params_put = {"part": "snippet"}

        body = {
            "id": YOUTUBE_CONFIG["video_id"],
            "snippet": {
                "title": title,
                "categoryId": "20"  # 20 = Gaming (по умолчанию)
            }
        }

        print(f"[YOUTUBE] Updating: title='{title}'")

        resp_put = make_youtube_request("PUT", url_put, headers=headers, params=params_put, json=body)
        resp_put.raise_for_status()

        print(f"[YOUTUBE] ✅ Success")
        return {"success": True, "message": "YouTube обновлен"}
    except Exception as e:
        error_msg = str(e)
        print(f"[YOUTUBE] ❌ Error: {error_msg}")
        return {"success": False, "error": f"YouTube: {error_msg}"}

# ==================== TROVO ====================

def get_trovo_category_id(category_name: str) -> Optional[str]:
    """Получает category_id Trovo по названию"""
    if not category_name:
        return None

    if not TROVO_CONFIG["access_token"]:
        return None

    try:
        url = "https://open-api.trovo.live/openplatform/searchcategory"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        body = {"query": category_name, "limit": 1}

        resp = make_trovo_request("POST", url, headers=headers, json=body)
        resp.raise_for_status()

        data = resp.json().get("category_info", [])
        if data:
            category_id = data[0]["id"]
            print(f"[TROVO] Found category ID: {category_id} for '{category_name}'")
            return category_id
    except Exception as e:
        print(f"[TROVO] Error getting category ID: {e}")

    return None

def update_trovo(title: str, category: str) -> Dict:
    """Обновляет название и категорию на Trovo"""
    try:
        if not TROVO_CONFIG["access_token"]:
            return {"success": False, "error": "Trovo token не настроен"}

        if not TROVO_CONFIG["channel_id"]:
            return {"success": False, "error": "Trovo channel_id не настроен"}

        category_id = get_trovo_category_id(category) if category else None

        url = "https://open-api.trovo.live/openplatform/channels/update"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        body = {
            "channel_id": int(TROVO_CONFIG["channel_id"]),
            "live_title": title
        }
        if category_id:
            body["category_id"] = category_id

        print(f"[TROVO] Updating: title='{title}', category_id={category_id}")

        resp = make_trovo_request("POST", url, headers=headers, json=body)
        resp.raise_for_status()

        print(f"[TROVO] ✅ Success")
        return {"success": True, "message": "Trovo обновлен"}
    except Exception as e:
        error_msg = str(e)
        print(f"[TROVO] ❌ Error: {error_msg}")
        return {"success": False, "error": f"Trovo: {error_msg}"}

# ==================== VK PLAY LIVE ====================

def update_vkplay(title: str, category: str) -> Dict:
    """Обновляет название на VK Play Live"""
    try:
        if not VKPLAY_CONFIG["access_token"]:
            return {"success": False, "error": "VK Play token не настроен"}
        
        url = f"https://live.vkvideo.ru/api/v2/streams/update"
        headers = {
            "Authorization": f"Bearer {VKPLAY_CONFIG['access_token']}",
            "Content-Type": "application/json"
        }
        
        body = {"title": title}
        if category:
            body["category"] = category
        
        print(f"[VKPLAY] Updating: title='{title}'")
        
        resp = requests.post(url, headers=headers, json=body, timeout=5)
        resp.raise_for_status()
        
        print(f"[VKPLAY] ✅ Success")
        return {"success": True, "message": "VK Play Live обновлен"}
    except Exception as e:
        error_msg = str(e)
        print(f"[VKPLAY] ❌ Error: {error_msg}")
        return {"success": False, "error": f"VK Play Live: {error_msg} (требуется настройка Chat Client)"}

# ==================== KICK ====================

def update_kick(title: str, category: str) -> Dict:
    """Обновляет название на Kick"""
    try:
        if not KICK_CONFIG["access_token"]:
            return {"success": False, "error": "Kick token не настроен"}
        
        if not KICK_CONFIG["channel_slug"]:
            return {"success": False, "error": "Kick channel_slug не настроен"}
        
        url = f"https://kick.com/api/v1/channels/{KICK_CONFIG['channel_slug']}"
        headers = {
            "Authorization": f"Bearer {KICK_CONFIG['access_token']}",
            "Content-Type": "application/json"
        }
        
        body = {"session_title": title}
        if category:
            body["category"] = category
        
        print(f"[KICK] Updating: title='{title}'")
        
        resp = requests.patch(url, headers=headers, json=body, timeout=5)
        resp.raise_for_status()
        
        print(f"[KICK] ✅ Success")
        return {"success": True, "message": "Kick обновлен"}
    except Exception as e:
        error_msg = str(e)
        print(f"[KICK] ❌ Error: {error_msg}")
        return {"success": False, "error": f"Kick: {error_msg}"}

# ==================== FLASK ROUTES ====================

@app.route("/")
def index():
    """Главная страница с UI панелью"""
    history = load_history()
    return render_template("index.html", history=history)

@app.route("/update", methods=["POST"])
def update():
    """Обновляет стрим на выбранных платформах"""
    data = request.json
    title = data.get("title", "").strip()
    category = data.get("category", "").strip()
    platforms = data.get("platforms", [])
    
    print(f"\n{'='*60}")
    print(f"📡 UPDATE REQUEST at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Title: '{title}'")
    print(f"   Category: '{category}'")
    print(f"   Platforms: {platforms}")
    print(f"{'='*60}")
    
    if not title:
        return jsonify({"success": False, "error": "Введите название стрима"}), 400
    
    if not platforms:
        return jsonify({"success": False, "error": "Выберите хотя бы одну платформу"}), 400
    
    results = {}
    
    try:
        if "twitch" in platforms:
            results["twitch"] = update_twitch(title, category)
        
        if "youtube" in platforms:
            results["youtube"] = update_youtube(title, category)
        
        if "trovo" in platforms:
            results["trovo"] = update_trovo(title, category)
        
        if "vkplay" in platforms:
            results["vkplay"] = update_vkplay(title, category)
        
        if "kick" in platforms:
            results["kick"] = update_kick(title, category)
        
        success_count = sum(1 for r in results.values() if r.get("success"))
        failed_count = len(results) - success_count
        
        print(f"\n📊 RESULT: {success_count} success, {failed_count} failed")
        print(f"{'='*60}\n")
        
        if success_count > 0:
            add_to_history(title, category)
            return jsonify({
                "success": True,
                "message": f"Обновлено на {success_count}/{len(results)} платформе(ах)",
                "details": results
            })
        else:
            return jsonify({
                "success": False,
                "error": "Ошибка обновления на всех платформах",
                "details": results
            }), 400
    
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        print(f"{'='*60}\n")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/history", methods=["GET"])
def history():
    """Возвращает историю"""
    return jsonify(load_history())

@app.route("/validate-config", methods=["GET"])
def validate_config():
    """Проверяет, какие конфиги заполнены"""
    config = check_config()
    return jsonify(config)

@app.before_request
def log_startup():
    """Логирование при старте"""
    if request.path == "/":
        print(f"\n{'='*60}")
        print("🚀 STREAM MANAGER STARTED")
        print(f"{'='*60}")
        print("\n📋 Configuration Status:")
        config = check_config()
        for platform, is_configured in config.items():
            status = "✅" if is_configured else "❌"
            print(f"   {status} {platform.upper()}")
        print(f"\n{'='*60}\n")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎬 STREAM MANAGER FOR OBS STUDIO")
    print("="*60)
    print("\nStarting Flask server...")
    print("\nAccess the dock in OBS at: http://127.0.0.1:5000/")
    print("\nPress CTRL+C to stop\n")
    
    app.run(host="0.0.0.0", port=5000, debug=False)
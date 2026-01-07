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
import hmac
import hashlib
import base64
from typing import Optional, Dict, List

app = Flask(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
# Переносите сюда свои токены (лучше использовать переменные окружения)

TWITCH_CONFIG = {
    "client_id": os.getenv("TWITCH_CLIENT_ID", "YOUR_CLIENT_ID"),
    "access_token": os.getenv("TWITCH_TOKEN", "YOUR_TOKEN"),
    "broadcaster_id": os.getenv("TWITCH_BROADCASTER_ID", "YOUR_BROADCASTER_ID"),
}

YOUTUBE_CONFIG = {
    "access_token": os.getenv("YOUTUBE_TOKEN", "YOUR_TOKEN"),
    "video_id": os.getenv("YOUTUBE_VIDEO_ID", "YOUR_VIDEO_ID"),  # ID трансляции
}

TROVO_CONFIG = {
    "client_id": os.getenv("TROVO_CLIENT_ID", "YOUR_CLIENT_ID"),
    "access_token": os.getenv("TROVO_TOKEN", "YOUR_TOKEN"),
    "channel_id": os.getenv("TROVO_CHANNEL_ID", "YOUR_CHANNEL_ID"),
}

VKPLAY_CONFIG = {
    "access_token": os.getenv("VKPLAY_TOKEN", "YOUR_TOKEN"),
    "channel_id": os.getenv("VKPLAY_CHANNEL_ID", "YOUR_CHANNEL_ID"),
}

KICK_CONFIG = {
    "access_token": os.getenv("KICK_TOKEN", "YOUR_TOKEN"),
    "channel_slug": os.getenv("KICK_CHANNEL_SLUG", "YOUR_CHANNEL"),
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
    except:
        return []

def save_history(history: List[Dict]) -> None:
    """Сохраняет историю в файл"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def add_to_history(title: str, category: str) -> None:
    """Добавляет запись в историю"""
    history = load_history()
    entry = {
        "title": title,
        "category": category,
        "timestamp": datetime.now().isoformat(timespec="seconds")
    }
    # Убираем дубликаты
    history = [h for h in history if not (h["title"] == title and h["category"] == category)]
    history.insert(0, entry)
    history = history[:MAX_HISTORY]
    save_history(history)

# ==================== TWITCH ====================

def get_twitch_game_id(game_name: str) -> Optional[str]:
    """Получает ID игры в Twitch по названию"""
    if not game_name:
        return None
    
    url = "https://api.twitch.tv/helix/games"
    headers = {
        "Client-ID": TWITCH_CONFIG["client_id"],
        "Authorization": f"Bearer {TWITCH_CONFIG['access_token']}"
    }
    params = {"name": game_name}
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if data:
            return data[0]["id"]
    except Exception as e:
        print(f"[TWITCH] Error getting game ID: {e}")
    
    return None

def update_twitch(title: str, category: str) -> Dict:
    """Обновляет название и категорию на Twitch"""
    try:
        game_id = get_twitch_game_id(category) if category else None
        
        url = "https://api.twitch.tv/helix/channels"
        headers = {
            "Client-ID": TWITCH_CONFIG["client_id"],
            "Authorization": f"Bearer {TWITCH_CONFIG['access_token']}",
            "Content-Type": "application/json"
        }
        params = {"broadcaster_id": TWITCH_CONFIG["broadcaster_id"]}
        
        body = {"title": title}
        if game_id:
            body["game_id"] = game_id
        
        resp = requests.patch(url, headers=headers, params=params, json=body, timeout=5)
        resp.raise_for_status()
        
        return {"success": True, "message": "Twitch обновлен"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== YOUTUBE ====================

def get_youtube_category_id(category_name: str) -> Optional[str]:
    """Получает categoryId YouTube по названию категории"""
    if not category_name:
        return None
    
    # Это упрощённый вариант - в реальности нужно делать поиск через API
    category_map = {
        "gaming": "20",
        "music": "10",
        "live": "29",
        "creative": "30",
    }
    return category_map.get(category_name.lower(), None)

def update_youtube(title: str, category: str) -> Dict:
    """Обновляет название на YouTube"""
    try:
        # Шаг 1: получаем текущий categoryId
        url_get = f"https://www.googleapis.com/youtube/v3/videos"
        headers = {
            "Authorization": f"Bearer {YOUTUBE_CONFIG['access_token']}",
            "Content-Type": "application/json"
        }
        params_get = {
            "part": "snippet",
            "id": YOUTUBE_CONFIG["video_id"],
            "fields": "items/snippet/categoryId"
        }
        
        resp_get = requests.get(url_get, headers=headers, params=params_get, timeout=5)
        resp_get.raise_for_status()
        
        data = resp_get.json().get("items", [])
        if not data:
            return {"success": False, "error": "Video not found"}
        
        category_id = data[0]["snippet"]["categoryId"]
        
        # Шаг 2: обновляем title
        url_put = f"https://www.googleapis.com/youtube/v3/videos"
        params_put = {"part": "snippet"}
        
        body = {
            "id": YOUTUBE_CONFIG["video_id"],
            "snippet": {
                "title": title,
                "categoryId": category_id
            }
        }
        
        resp_put = requests.put(url_put, headers=headers, params=params_put, json=body, timeout=5)
        resp_put.raise_for_status()
        
        return {"success": True, "message": "YouTube обновлен"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== TROVO ====================

def get_trovo_category_id(category_name: str) -> Optional[str]:
    """Получает category_id Trovo по названию"""
    if not category_name:
        return None
    
    try:
        url = "https://open-api.trovo.live/openplatform/searchcategory"
        headers = {
            "Accept": "application/json",
            "Client-ID": TROVO_CONFIG["client_id"],
            "Content-Type": "application/json"
        }
        body = {"query": category_name, "limit": 1}
        
        resp = requests.post(url, headers=headers, json=body, timeout=5)
        resp.raise_for_status()
        
        data = resp.json().get("category_info", [])
        if data:
            return data[0]["id"]
    except Exception as e:
        print(f"[TROVO] Error getting category ID: {e}")
    
    return None

def update_trovo(title: str, category: str) -> Dict:
    """Обновляет название и категорию на Trovo"""
    try:
        category_id = get_trovo_category_id(category) if category else None
        
        url = "https://open-api.trovo.live/openplatform/channels/update"
        headers = {
            "Accept": "application/json",
            "Client-ID": TROVO_CONFIG["client_id"],
            "Authorization": f"OAuth {TROVO_CONFIG['access_token']}",
            "Content-Type": "application/json"
        }
        
        body = {
            "channel_id": int(TROVO_CONFIG["channel_id"]),
            "live_title": title
        }
        if category_id:
            body["category_id"] = category_id
        
        resp = requests.post(url, headers=headers, json=body, timeout=5)
        resp.raise_for_status()
        
        return {"success": True, "message": "Trovo обновлен"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== VK PLAY LIVE ====================

def update_vkplay(title: str, category: str) -> Dict:
    """Обновляет название на VK Play Live"""
    try:
        # VK Play Live API работает через chat client (более сложная интеграция)
        # Это упрощённый вариант через REST API (если доступен)
        url = f"https://live.vkvideo.ru/api/v2/streams/{VKPLAY_CONFIG['channel_id']}/update"
        
        headers = {
            "Authorization": f"Bearer {VKPLAY_CONFIG['access_token']}",
            "Content-Type": "application/json"
        }
        
        body = {"title": title}
        if category:
            body["category"] = category
        
        resp = requests.post(url, headers=headers, json=body, timeout=5)
        resp.raise_for_status()
        
        return {"success": True, "message": "VK Play Live обновлен"}
    except Exception as e:
        # Если REST API недоступен, вернём информацию об ошибке
        return {"success": False, "error": f"VK Play Live: {str(e)}. Требуется ручная интеграция chat client."}

# ==================== KICK ====================

def update_kick(title: str, category: str) -> Dict:
    """Обновляет название на Kick (через неофициальный API)"""
    try:
        # Kick API всё ещё развивается, это упрощённый вариант
        url = f"https://kick.com/api/v1/channels/{KICK_CONFIG['channel_slug']}"
        
        headers = {
            "Authorization": f"Bearer {KICK_CONFIG['access_token']}",
            "Content-Type": "application/json"
        }
        
        body = {"session_title": title}
        if category:
            body["category"] = category
        
        resp = requests.patch(url, headers=headers, json=body, timeout=5)
        resp.raise_for_status()
        
        return {"success": True, "message": "Kick обновлен"}
    except Exception as e:
        return {"success": False, "error": f"Kick: {str(e)}"}

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
        
        # Проверяем, успешно ли обновилось хотя бы на одной платформе
        success_count = sum(1 for r in results.values() if r.get("success"))
        
        if success_count > 0:
            add_to_history(title, category)
            return jsonify({
                "success": True,
                "message": f"Обновлено на {success_count} платформе(ах)",
                "details": results
            })
        else:
            return jsonify({
                "success": False,
                "error": "Ошибка обновления на всех платформах",
                "details": results
            }), 400
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/history", methods=["GET"])
def history():
    """Возвращает историю"""
    return jsonify(load_history())

@app.route("/validate-config", methods=["GET"])
def validate_config():
    """Проверяет, заполнены ли конфиги"""
    configs = {
        "twitch": TWITCH_CONFIG["client_id"] != "YOUR_CLIENT_ID",
        "youtube": YOUTUBE_CONFIG["access_token"] != "YOUR_TOKEN",
        "trovo": TROVO_CONFIG["client_id"] != "YOUR_CLIENT_ID",
        "vkplay": VKPLAY_CONFIG["access_token"] != "YOUR_TOKEN",
        "kick": KICK_CONFIG["access_token"] != "YOUR_TOKEN",
    }
    return jsonify(configs)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
import os
import json

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.topology_tormentor')

def get_ai_config(user_id="default"):
    path = os.path.join(CONFIG_DIR, f'ai_config_{user_id}.json')
    if not os.path.exists(path):
        return {
            "active_profile": "Default", 
            "profiles": [
                {"name": "Default", "provider": "Ollama", "api_key": "", "model": "network-assistant-ultimate:latest"}
            ]
        }
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return {
            "active_profile": "Default", 
            "profiles": [
                {"name": "Default", "provider": "Ollama", "api_key": "", "model": "network-assistant-ultimate:latest"}
            ]
        }

def save_ai_config(cfg, user_id="default"):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    path = os.path.join(CONFIG_DIR, f'ai_config_{user_id}.json')
    with open(path, 'w') as f:
        json.dump(cfg, f, indent=4)

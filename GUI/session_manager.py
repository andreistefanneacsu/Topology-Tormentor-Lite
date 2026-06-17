import os
import json

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.topology_tormentor')
SESSION_PATH = os.path.join(CONFIG_DIR, 'session.json')

def save_session(user_data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(SESSION_PATH, 'w') as f:
        json.dump(user_data, f, indent=4)

def load_session():
    if not os.path.exists(SESSION_PATH):
        return None
    try:
        with open(SESSION_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def clear_session():
    if os.path.exists(SESSION_PATH):
        try:
            os.remove(SESSION_PATH)
        except Exception:
            pass

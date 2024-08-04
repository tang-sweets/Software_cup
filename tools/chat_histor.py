import os
import json

def save_data(username, chat_name, data):
    path = f"chats/{username}"
    if not chat_name.endswith(".json"):
        chat_name += ".json"
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, chat_name), 'w') as f:
        json.dump({"history": data}, f)

def load_data(username, chat_name):
    path = f"chats/{username}"
    if not chat_name.endswith(".json"):
        chat_name += ".json"
    with open(os.path.join(path, chat_name), 'r') as f:
        return json.load(f)["history"]

def get_history_chats(username):
    path = f"chats/{username}"
    return [f[:-5] for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f.endswith(".json")]

def remove_data(username, chat_name):
    path = f"chats/{username}"
    if not chat_name.endswith(".json"):
        chat_name += ".json"
    os.remove(os.path.join(path, chat_name))

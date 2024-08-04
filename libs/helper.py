import json
import os
import streamlit as st

def get_history_chats(path: str) -> list:
    os.makedirs(path, exist_ok=True)
    files = [f for f in os.listdir(path) if f.endswith('.json')]
    files_with_time = [(f, os.stat(os.path.join(path, f)).st_ctime) for f in files]
    sorted_files = sorted(files_with_time, key=lambda x: x[1], reverse=True)
    chat_names = [os.path.splitext(f[0])[0] for f in sorted_files]
    return chat_names

def save_data(path: str, file_name: str, history: list, paras: dict, contexts: dict, **kwargs):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, f"{file_name}.json"), 'w', encoding='utf-8') as f:
        json.dump({"history": history, "paras": paras, "contexts": contexts, **kwargs}, f)

def load_data(path: str, file_name: str) -> dict:
    try:
        with open(os.path.join(path, f"{file_name}.json"), 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        return {"history": [], "paras": {}, "contexts": {}}

def remove_data(path: str, chat_name: str):
    try:
        os.remove(os.path.join(path, f"{chat_name}.json"))
    except FileNotFoundError:
        pass

    # 清除缓存
    try:
        st.session_state.pop('history' + chat_name)
    except KeyError:
        pass

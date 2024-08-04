import os
import json
import requests
import streamlit as st
import threading
from tools.chat_histor import save_data, load_data, get_history_chats, remove_data

API_KEY = st.secrets["api"]["Baichuan_key"]
BASE_URL = "https://api.baichuan-ai.com/v1"
CHARACTERS_FILE = "static/characters/characters.json"

def load_characters():
    if os.path.exists(CHARACTERS_FILE):
        with open(CHARACTERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_characters(characters):
    with open(CHARACTERS_FILE, "w", encoding="utf-8") as f:
        json.dump(characters, f, ensure_ascii=False, indent=4)

def stream_response(api_key, model, character_id, message_history, username):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "character_profile": {"character_id": character_id},
        "messages": message_history,
        "temperature": st.session_state.get("temperature", 0.9),  # 默认值设置为0.9
        "top_p": st.session_state.get("top_p", 0.3),
        "stream": True
    }
    response = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=data, stream=True)

    if response.status_code == 200:
        assistant_response = st.empty()
        assistant_content = ""

        for chunk in response.iter_lines(decode_unicode=False):
            if chunk:
                chunk = chunk.decode('utf-8')
                if chunk.startswith("data: "):
                    chunk_data = chunk[len("data: "):].strip()
                    if chunk_data == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(chunk_data)
                        chunk_message = chunk_json['choices'][0]['delta']
                        if 'content' in chunk_message and chunk_message['content']:
                            assistant_content += chunk_message['content']
                            assistant_response.markdown(assistant_content)
                    except json.JSONDecodeError as e:
                        st.error(f"JSONDecodeError: {e}")
                        continue
        if assistant_content.strip():
            st.session_state["messages"].append({"role": "assistant", "content": assistant_content})
            if st.session_state["chat_name"]:
                save_data(username, st.session_state["chat_name"], message_history)
            st.experimental_rerun()
    else:
        st.error(f"Error: {response.status_code}, {response.text}")

def main(__login__obj):
    if "chat_name" not in st.session_state:
        st.session_state["chat_name"] = None
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "uploaded_file" not in st.session_state:
        st.session_state["uploaded_file"] = None
    if "file_id" not in st.session_state:
        st.session_state["file_id"] = None

    username = __login__obj.get_username()

    st.title('角色模拟')

    with st.sidebar:
        api_key = st.secrets["api"]["Baichuan_key"]
        base_url = 'https://api.baichuan-ai.com/v1'

        existing_chats = get_history_chats(username)
        selected_chat = st.selectbox("选择聊天记录", [""] + existing_chats)

        if selected_chat and selected_chat != st.session_state.get("chat_name"):
            st.session_state["chat_name"] = selected_chat
            st.session_state["messages"] = load_data(username, selected_chat)
            st.experimental_rerun()

        new_chat_name = st.text_input("新建聊天名称", "")

        cols = st.columns(3)
        with cols[0]:
            if st.button("新建聊天"):
                if not new_chat_name:
                    new_chat_name = f"chat_{len(existing_chats) + 1}"
                st.session_state["chat_name"] = new_chat_name
                st.session_state["messages"] = []
                save_data(username, new_chat_name, st.session_state["messages"])
                st.experimental_rerun()

        with cols[1]:
            if st.button("删除聊天") and selected_chat:
                remove_data(username, selected_chat)
                st.experimental_rerun()

        model = "Baichuan-NPC-Turbo"

        st.write("选择角色分类和角色:")
        characters = load_characters()
        category = st.selectbox("选择角色分类", list(characters.keys()))
        role = st.selectbox("选择角色", list(characters[category].keys()))

        character_id = characters[category][role]['id']
        character_description = characters[category][role]['description']
        st.write(f"角色描述: {character_description}")

        # 这里移除了温度滑块
        # st.session_state["temperature"] = st.slider("温度", min_value=0.0, max_value=1.0, value=0.3, step=0.1, help="控制生成结果的发散性和集中性。数值越小，越集中；数值越大，越发散。")


    st.write(f"当前使用的角色是：{role} (ID: {character_id})")

    for msg in st.session_state["messages"]:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("输入你的消息："):
        if prompt.strip():
            st.session_state["messages"].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": model,
                "character_profile": {"character_id": character_id},
                "messages": st.session_state["messages"],
                "temperature": st.session_state.get("temperature", 0.9),  # 确保设置了默认温度值
                "stream": True
            }

            response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, stream=True)

            if response.status_code == 200:
                assistant_response = st.empty()
                assistant_content = ""

                for chunk in response.iter_lines(decode_unicode=False):
                    if chunk:
                        chunk = chunk.decode('utf-8')
                        if chunk.startswith("data: "):
                            chunk_data = chunk[len("data: "):].strip()
                            if chunk_data == "[DONE]":
                                break
                            try:
                                chunk_json = json.loads(chunk_data)
                                chunk_message = chunk_json['choices'][0]['delta']
                                if 'content' in chunk_message and chunk_message['content']:
                                    assistant_content += chunk_message['content']
                                    assistant_response.markdown(assistant_content)
                            except json.JSONDecodeError as e:
                                st.error(f"JSONDecodeError: {e}")
                                continue
                if assistant_content.strip():
                    st.session_state["messages"].append({"role": "assistant", "content": assistant_content})
                    if st.session_state["chat_name"]:
                        save_data(username, st.session_state["chat_name"], st.session_state["messages"])
                    st.experimental_rerun()  # 重新加载页面以确保组件正确渲染
            else:
                st.error(f"Error: {response.status_code}, {response.text}")

            if st.session_state["chat_name"]:
                save_data(username, st.session_state["chat_name"], st.session_state["messages"])

if __name__ == "__main__":
    main(__login__obj)

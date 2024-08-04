import os
import json
import requests
import streamlit as st
import threading
import re
from tools.chat_histor import save_data, load_data, get_history_chats, remove_data
from tools.audio_recognition import transcribe_audio, record_audio

API_KEY = st.secrets["api"]["Baichuan_key"]
UPLOAD_FILE_URL = "https://api.baichuan-ai.com/v1/files"
CHAT_COMPLETION_URL = "https://api.baichuan-ai.com/v1/chat/completions"
KNOWLEDGE_BASES_URL = "https://api.baichuan-ai.com/v1/kbs"


def list_knowledge_bases():
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    response = requests.get(KNOWLEDGE_BASES_URL, headers=headers)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        st.error(f"获取知识库列表失败: {response.status_code}, {response.text}")
        return []


def upload_file(file, purpose):
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    files = {
        "file": file,
        "purpose": (None, purpose)
    }
    response = requests.post(UPLOAD_FILE_URL, headers=headers, files=files)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"文件上传失败: {response.status_code}, {response.text}")
        return None


def get_parsed_content(file_id):
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    response = requests.get(f"{UPLOAD_FILE_URL}/{file_id}/parsed-content", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"获取文件解析内容失败: {response.status_code}, {response.text}")
        return None


def create_kb(data):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    try:
        response = requests.post(KNOWLEDGE_BASES_URL, data=json.dumps(data), headers=headers, timeout=30)
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"创建知识库时发生错误: {e}")
        return None


def associate_file_with_kb(kb_id, file_ids):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    url = f"{KNOWLEDGE_BASES_URL}/{kb_id}/files"
    data = {"file_ids": file_ids}
    try:
        response = requests.post(url, data=json.dumps(data), headers=headers, timeout=30)
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"关联文件到知识库时发生错误: {e}")
        return None


def ask_question(question, kb_ids, use_knowledge_base_only, use_web_search):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    tools = []

    if kb_ids:
        retrieval_tool = {
            "type": "retrieval",
            "retrieval": {
                "kb_ids": kb_ids
            }
        }
        if use_knowledge_base_only:
            retrieval_tool["retrieval"]["answer_mode"] = "knowledge-base-only"
        tools.append(retrieval_tool)

    if use_web_search:
        tools.append({
            "type": "web_search",
            "web_search": {
                "enable": True,
                "search_mode": "performance_first"
            }
        })

    data = {
        "model": st.session_state["current_model_Bai"],
        "messages": [{"role": "user", "content": question}],
        "tools": tools,
        "stream": True
    }

    response = requests.post(CHAT_COMPLETION_URL, json=data, headers=headers, stream=True)
    return response


def handle_audio_input(api_key, chosen_model, message_history, username):
    if 'is_recording' not in st.session_state:
        st.session_state['is_recording'] = False

    if st.button("🎙️语音输入", key="audio_input"):
        if not st.session_state['is_recording']:
            st.session_state['is_recording'] = True
            st.info("聆听中。。。再次单击该按钮可停止。")
            threading.Thread(target=record_audio, args=("static/wav/temp.wav", 30)).start()
        else:
            st.session_state['is_recording'] = False
            st.info("语音输入完成。单击“📝”开始转录。")
            os.system("taskkill /im audiod.exe /f")

    if st.button("📝转录语音", key="transcribe_audio"):
        st.info("正在转录，请稍候...")
        try:
            transcription = transcribe_audio("static/wav/temp.wav")
            st.success("转录完成")
            st.chat_message("user").write(transcription)
            message_history.append({"role": "user", "content": transcription})
            stream_response(api_key, chosen_model, message_history, username)
        except Exception as e:
            st.error(e)


def stream_response(api_key, model, message_history, username):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"model": model, "messages": message_history, "stream": True}
    response = requests.post(CHAT_COMPLETION_URL, headers=headers, json=data, stream=True)

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
        st.session_state["messages"] = [
            {"role": "system", "content": "你是知识库助手。你能够借助知识库进行问答，为用户提供安全、有帮助且准确的回答。你可以根据用户的问题，从相关的知识库中检索信息，并结合你的内置知识，为用户提供详细、准确的解答。无论用户提出什么问题，你都应该尽可能全面地解答，同时确保回答的安全性和实用性。"}
        ]
    if "uploaded_file" not in st.session_state:
        st.session_state["uploaded_file"] = None
    if "file_id" not in st.session_state:
        st.session_state["file_id"] = None
    if "selected_kb" not in st.session_state:
        st.session_state["selected_kb"] = None

    username = __login__obj.get_username()

    st.title('知识库助手')

    with st.sidebar:
        api_key = st.secrets["api"]["Baichuan_key"]
        base_url = 'https://api.baichuan-ai.com/v1'

        st.write("上传文件自动创建知识库")
        # 文件上传组件
        uploaded_file = st.file_uploader("上传文件", type=["pdf", "doc", "docx", "txt", "excel"])

        if "current_model_Bai" not in st.session_state:
            st.session_state["current_model_Bai"] = "Baichuan4"

        st.write("选择模型:")

        model_option = [
            "Baichuan4",
            "Baichuan3-Turbo",
            "Baichuan3-Turbo-128k",
            "Baichuan2-Turbo",
            "Baichuan2-Turbo-192k"
        ]

        model = st.selectbox(
            "模型",
            model_option,
            index=model_option.index(st.session_state["current_model_Bai"]),
        )

        st.session_state["current_model_Bai"] = model

        # 知识库选择
        knowledge_bases = list_knowledge_bases()
        kb_names = [kb["name"] for kb in knowledge_bases]
        selected_kb_name = st.selectbox("选择知识库", kb_names)
        if selected_kb_name:
            selected_kb = next(kb for kb in knowledge_bases if kb["name"] == selected_kb_name)
            st.session_state["selected_kb"] = selected_kb["id"]

        # 仅使用知识库内容回答的开关
        use_knowledge_base_only = st.checkbox("仅使用知识库内容进行回答", value=False)
        st.session_state["use_knowledge_base_only"] = use_knowledge_base_only

        # 启用联网检索的开关
        use_web_search = st.checkbox("启用联网检索", value=False)
        st.session_state["use_web_search"] = use_web_search

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
                st.session_state["messages"] = [
                    {"role": "system",
                     "content": "你是知识库助手。你能够借助知识库进行问答，为用户提供安全、有帮助且准确的回答。你可以根据用户的问题，从相关的知识库中检索信息，并结合你的内置知识，为用户提供详细、准确的解答。无论用户提出什么问题，你都应该尽可能全面地解答，同时确保回答的安全性和实用性。"}
                ]
                save_data(username, new_chat_name, st.session_state["messages"])
                st.experimental_rerun()

        with cols[1]:
            if st.button("删除聊天") and selected_chat:
                remove_data(username, selected_chat)
                st.experimental_rerun()


    st.write(f"当前使用的模型是：{st.session_state['current_model_Bai']}")

    for msg in st.session_state["messages"]:
        st.chat_message(msg["role"]).write(msg["content"])

    if uploaded_file and uploaded_file != st.session_state["uploaded_file"]:
        st.session_state["uploaded_file"] = uploaded_file
        purpose = "file-parsing"
        with st.spinner("上传中..."):
            result = upload_file(uploaded_file, purpose)
            if result and 'id' in result:
                file_id = result['id']
                st.session_state["file_id"] = file_id

                # 处理文件名，确保符合知识库名称要求
                kb_name = re.sub(r'[^\u4E00-\u9FA5A-Za-z0-9_]', '_', uploaded_file.name)
                kb_name = kb_name[:50]

                # 创建知识库
                kb_data = {
                    "name": kb_name,
                    "description": f"知识库创建于文件 {uploaded_file.name} 上传",
                    "split_type": 1
                }
                response = create_kb(kb_data)
                if response and response.status_code == 200:
                    kb_id = response.json().get("id")
                    st.session_state["kb_id"] = kb_id
                    st.success("知识库创建成功！")

                    # 关联文件到知识库
                    associate_response = associate_file_with_kb(kb_id, [file_id])
                    if associate_response and associate_response.status_code == 200:
                        st.success("文件成功关联到知识库！")
                    else:
                        st.error(f"文件关联到知识库失败: {associate_response.status_code}, {associate_response.text}")
                else:
                    st.error(f"知识库创建失败: {response.status_code}, {response.text}")
            else:
                st.error(f"文件上传失败: {result['status_code']}, {result['text']}")

    if prompt := st.chat_input("输入你的消息："):
        if prompt.strip():
            st.session_state["messages"].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            kb_ids = [st.session_state["selected_kb"]] if st.session_state["selected_kb"] else []

            response = ask_question(prompt, kb_ids,
                                    st.session_state["use_knowledge_base_only"],
                                    st.session_state["use_web_search"])

            if response and response.status_code == 200:
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

    handle_audio_input(api_key, st.session_state["current_model_Bai"], st.session_state["messages"], username)


if __name__ == "__main__":
    main(__login__obj)

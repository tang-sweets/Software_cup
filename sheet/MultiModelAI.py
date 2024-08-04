import json
import os
import streamlit as st
import requests
import threading

from libs.contexts import set_context
from tools.chat_histor import get_history_chats, save_data, load_data, remove_data
from tools.file_upload import handle_file_upload
from tools.audio_recognition import transcribe_audio, record_audio

MODEL_API_URLS = {
    "GPT": "https://api.bianxieai.com/v1/chat/completions",
    "Deepseek": "https://api.deepseek.com/v1/chat/completions",
    "Yi": "https://api.lingyiwanwu.com/v1/chat/completions",
    "Moonshot": "https://api.moonshot.cn/v1/chat/completions",
    "Baichuan": "https://api.baichuan-ai.com/v1/chat/completions"
}

MODEL_API_KEYS = {
    "GPT": st.secrets["api"]["bianxie_key"],
    "Gemini": st.secrets["api"]["bianxie_key"],
    "Claude": st.secrets["api"]["bianxie_key"],
    "Deepseek": st.secrets["api"]["Deepseek_key"],
    "Yi": st.secrets["api"]["Yi_key"],
    "Moonshot": st.secrets["api"]["Moonshot_key"],
    "Baichuan": st.secrets["api"]["Baichuan_key"]
}

def handle_audio_input(api_key, message_history, username):
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
            deepseek_api_key = MODEL_API_KEYS["Deepseek"]
            stream_response(deepseek_api_key, "deepseek-chat", message_history, username)
        except Exception as e:
            st.error(e)
            st.write(f"转录过程中出现错误: {e}")

def stream_response(api_key, chosen_model, message_history, username):
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {"model": chosen_model, "messages": message_history, "stream": True}

        url = MODEL_API_URLS.get("Deepseek")
        if not url:
            raise ValueError(f"无效的模型: {chosen_model}")

        response = requests.post(url, headers=headers, json=data, stream=True)

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
                            if 'choices' in chunk_json and chunk_json['choices']:
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
    except Exception as e:
        st.error(f"请求过程中出现错误: {e}")

def transcribe_audio(file_path):
    """语音识别函数，将音频文件上传并返回识别文本"""
    url = 'https://api.bianxieai.com/v1/audio/transcriptions'
    headers = {
        "Authorization": f"Bearer {st.secrets['api']['bianxie_key']}"
    }
    files = {
        "file": ("audio.wav", open(file_path, "rb")),
        "model": (None, "whisper-1")
    }

    response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        return response.json().get('text', '')
    else:
        raise Exception(f"Failed to get translation: {response.status_code} - {response.text}")

def main(__login__obj):
    username = __login__obj.get_username()

    if "chat_name" not in st.session_state:
        st.session_state["chat_name"] = None
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "preset_sent" not in st.session_state:
        st.session_state["preset_sent"] = False

    message_history = st.session_state["messages"]

    with st.sidebar:
        st.title("聊天设置")

        existing_chats = get_history_chats(username)
        selected_chat = st.selectbox("选择聊天记录", [""] + existing_chats, index=0)

        if selected_chat and selected_chat != st.session_state.get("chat_name"):
            st.session_state["chat_name"] = selected_chat
            st.session_state["messages"] = load_data(username, selected_chat)
            st.session_state["preset_sent"] = False
            st.experimental_rerun()

        new_chat_name = st.text_input("新建聊天名称", "")

        cols = st.columns(2)
        with cols[0]:
            if st.button("新建聊天"):
                if not new_chat_name:
                    new_chat_name = f"chat_{len(existing_chats) + 1}"
                st.session_state["chat_name"] = new_chat_name
                st.session_state["messages"] = []
                st.session_state["preset_sent"] = False
                save_data(username, new_chat_name, st.session_state["messages"])
                st.experimental_rerun()

        with cols[1]:
            if st.button("删除聊天") and selected_chat:
                remove_data(username, selected_chat)
                st.experimental_rerun()

        api_key = MODEL_API_KEYS["Moonshot"]
        base_url = "https://api.moonshot.cn/v1"
        handle_file_upload(api_key, base_url, username, message_history)

        model_options = {
            "GPT": ["gpt-3.5-turbo", "gpt-4", "gpt-4o", 'gpt-4-all'],
            "Deepseek": ["deepseek-chat", "deepseek-coder"],
            "Yi": ["yi-large", "yi-medium", "yi-medium-200k", "yi-spark", "yi-large-rag", "yi-large-turbo",
                   "yi-large-preview"],
            "Moonshot": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
            "Baichuan": ["Baichuan4", "Baichuan3-Turbo", "Baichuan3-Turbo-128k", "Baichuan2-Turbo",
                         "Baichuan2-Turbo-192k"]
        }

        if "current_model_category" not in st.session_state or st.session_state[
            "current_model_category"] not in model_options:
            st.session_state["current_model_category"] = "GPT"
        if "current_model_chat" not in st.session_state or st.session_state["current_model_chat"] not in model_options[
            st.session_state["current_model_category"]]:
            st.session_state["current_model_chat"] = model_options[st.session_state["current_model_category"]][0]

        chosen_category = st.selectbox("选择模型类别", list(model_options.keys()),
                                       index=list(model_options.keys()).index(
                                           st.session_state["current_model_category"]))

        if st.session_state["current_model_chat"] not in model_options[chosen_category]:
            st.session_state["current_model_chat"] = model_options[chosen_category][0]

        chosen_model = st.selectbox("选择型号", model_options[chosen_category],
                                    index=model_options[chosen_category].index(st.session_state["current_model_chat"]))

        st.session_state["current_model_category"] = chosen_category
        st.session_state["current_model_chat"] = chosen_model

        scene_options = {
            "日常对话": {"max_tokens": 512, "top_p": 0.8, "temperature": 0.7},
            "写代码": {"max_tokens": 2048, "top_p": 0.3, "temperature": 0.2},
            "短文本生成": {"max_tokens": 1024, "top_p": 0.5, "temperature": 0.5},
            "文章生成": {"max_tokens": 2048, "top_p": 0.7, "temperature": 0.6},
            "创作诗歌或故事": {"max_tokens": 2048, "top_p": 0.9, "temperature": 1.0},
            "长篇小说": {"max_tokens": 4096, "top_p": 0.9, "temperature": 1.2},
            "技术问答": {"max_tokens": 1024, "top_p": 0.4, "temperature": 0.3},
            "产品推荐": {"max_tokens": 1024, "top_p": 0.6, "temperature": 0.5},
            "新闻摘要": {"max_tokens": 1024, "top_p": 0.7, "temperature": 0.6},
            "客户支持": {"max_tokens": 1024, "top_p": 0.5, "temperature": 0.4}
        }

        chosen_scene = st.selectbox("选择应用场景", list(scene_options.keys()), index=0)

        max_tokens = scene_options[chosen_scene]["max_tokens"]
        top_p = scene_options[chosen_scene]["top_p"]
        temperature = scene_options[chosen_scene]["temperature"]

        use_preset = st.checkbox("使用预设角色")
        if use_preset:
            chosen_role = st.selectbox("选择预设角色", ["请选择"] + list(set_context.keys()))
            if chosen_role != "请选择" and not st.session_state["preset_sent"]:
                preset_message = {"role": "system", "content": set_context[chosen_role]}
                message_history.append(preset_message)
                st.session_state["preset_sent"] = True

        api_key = MODEL_API_KEYS[chosen_category]

    st.write(f"当前使用的模型: {st.session_state['current_model_category']} - {st.session_state['current_model_chat']}")

    for msg in message_history:
        st.chat_message(msg["role"]).write(msg["content"])


    if prompt := st.chat_input("输入您的消息:"):
        chosen_category = st.session_state["current_model_category"]
        chosen_model = st.session_state["current_model_chat"]
        api_key = MODEL_API_KEYS[chosen_category]

        if not api_key:
            st.stop()

        with st.spinner("处理中..."):
            message_history.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            if st.session_state["chat_name"]:
                save_data(username, st.session_state["chat_name"], message_history)

            chat_url = MODEL_API_URLS[chosen_category]
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            data = {
                "model": chosen_model,
                "messages": message_history,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "temperature": temperature,
                "stream": True
            }
            response = requests.post(chat_url, json=data, headers=headers, stream=True)

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
                                if 'choices' in chunk_json and chunk_json['choices']:
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
                    st.experimental_rerun()
            else:
                st.error(f"Failed to fetch response from AI API: {response.status_code}, {response.text}")

            if st.session_state["chat_name"]:
                save_data(username, st.session_state["chat_name"], message_history)

    handle_audio_input(api_key, message_history, username)

if __name__ == "__main__":
    main(__login__obj)

import hashlib
import os
import time

import requests
import json
import streamlit as st
import threading
import sounddevice as sd
import wavio
from tools.chat_histor import save_data, load_data, get_history_chats, remove_data

# 设置 API Key
API_KEY = st.secrets["api"]["bianxie_key"]
TIANGONG_APP_KEY = st.secrets["api"]["Tiangong_key"]
TIANGONG_APP_SECRET = st.secrets["api"]["Tiangong_secret"]
YI_API_KEY = st.secrets["api"]["Yi_key"]
BAICHUAN_API_KEY = st.secrets["api"]["Baichuan_key"]
BAICHUAN_API_URL = "https://api.baichuan-ai.com/v1/"

def record_audio(file_path, duration=30, fs=44100):
    """录音函数，将录音保存到指定文件路径"""
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=2)
    sd.wait()  # 等待录音结束
    wavio.write(file_path, recording, fs, sampwidth=2)

def transcribe_audio(file_path):
    """语音识别函数，将音频文件上传并返回识别文本"""
    url = 'https://api.bianxieai.com/v1/audio/transcriptions'
    headers = {
        "Authorization": f"Bearer {API_KEY}"
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

def get_signature(app_key, app_secret):
    """生成签名"""
    timestamp = str(int(time.time()))
    sign_content = app_key + app_secret + timestamp
    return hashlib.md5(sign_content.encode('utf-8')).hexdigest(), timestamp

def format_response(content):
    """格式化输出内容"""
    content = content.replace('search', 'search\n')
    return content

def stream_response(app_key, app_secret, message_history, username, prompt):
    """流式响应函数，处理与API的交互并实时显示响应内容"""
    timestamp = str(int(time.time()))
    sign_content = app_key + app_secret + timestamp
    sign_result = hashlib.md5(sign_content.encode('utf-8')).hexdigest()

    headers = {
        "app_key": app_key,
        "timestamp": timestamp,
        "sign": sign_result,
        "Content-Type": "application/json",
    }

    data = {
        "messages": message_history,
        "intent": "",
        "max_tokens": st.session_state.get("max_tokens", 2048),
        "top_p": st.session_state.get("top_p", 0.9),
        "temperature": st.session_state.get("temperature", 0.3)
    }

    url = 'https://api-maas.singularity-ai.com/sky-work/api/v1/chat'
    response = requests.post(url, headers=headers, json=data, stream=True)

    if response.status_code == 200:
        assistant_response = st.empty()
        assistant_content = ""
        seen_texts = set()

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8').strip()
                if line.startswith("data: "):
                    line = line[len("data: "):].strip()
                if line == "[DONE]":
                    break
                if not line:
                    continue
                try:
                    chunk_json = json.loads(line)
                    if 'arguments' in chunk_json and 'messages' in chunk_json['arguments'][0]:
                        for message in chunk_json['arguments'][0]['messages']:
                            if 'text' in message:
                                if message['text'] not in seen_texts:
                                    seen_texts.add(message['text'])
                                    assistant_content += message['text']
                                    formatted_content = format_response(assistant_content)
                                    assistant_response.markdown(formatted_content)
                except json.JSONDecodeError as e:
                    st.error(f"JSONDecodeError: {e}")
                    st.write(line)
        if assistant_content.strip():
            st.session_state["messages"].append({"role": "assistant", "content": assistant_content})
            if st.session_state["chat_name"]:
                save_data(username, st.session_state["chat_name"], message_history)
            st.experimental_rerun()
    else:
        st.error(f"Error: {response.status_code}, {response.text}")

def yi_stream_response(api_key, model, message_history, username):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"model": model, "messages": message_history, "temperature": st.session_state.get("temperature", 0.9), "top_p": st.session_state.get("top_p", 0.3), "stream": True}
    response = requests.post(f"https://api.lingyiwanwu.com/v1/chat/completions", headers=headers, json=data, stream=True)

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

def baichuan_stream_response(api_key, model, message_history, username):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": message_history,
        "temperature": st.session_state.get("temperature", 0.3),
        "stream": True,
        "tools": [{
            "type": "web_search",
            "web_search": {
                "enable": True,
                "search_mode": "performance_first"
            }
        }]
    }
    response = requests.post(BAICHUAN_API_URL + "chat/completions", headers=headers, json=data, stream=True)

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

def handle_audio_input(app_key, app_secret, message_history, username):
    """处理音频输入并执行相应操作"""
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
            if st.session_state["selected_model"] == "SkyChat-3.0":
                stream_response(app_key, app_secret, message_history, username, transcription)
            elif st.session_state["selected_model"] == "Baichuan4":
                baichuan_stream_response(BAICHUAN_API_KEY, "Baichuan4", message_history, username)
            else:
                yi_stream_response(YI_API_KEY, st.session_state["current_model_Yi"], message_history, username)
            save_data(username, st.session_state["chat_name"], message_history)
            st.experimental_rerun()
        except Exception as e:
            st.error(e)
            st.write(f"转录过程中出现错误: {e}")

def main(__login__obj):
    """主函数，初始化应用程序并处理用户交互"""
    # 初始化会话状态
    if "chat_name" not in st.session_state:
        st.session_state["chat_name"] = None
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "preset_sent" not in st.session_state:
        st.session_state["preset_sent"] = False

    # 获取用户名
    username = __login__obj.get_username()

    st.title('智能联网助手')

    # 侧边栏输入 API 密钥和设置
    with st.sidebar:
        app_key = TIANGONG_APP_KEY
        app_secret = TIANGONG_APP_SECRET
        url = 'https://api-maas.singularity-ai.com/sky-work/api/v1/chat'

        st.sidebar.title("选择功能")
        function_option = ["实时天气查询", "新闻搜索和摘要", "实时股票行情", "旅游景点推荐", "百科"]
        chosen_function = st.sidebar.selectbox("功能", function_option)

        st.write("选择模型:")

        model_option = [
            "SkyChat-3.0",
            "yi-large-rag",
            "Baichuan4"
        ]

        model = st.selectbox(
            "模型",
            model_option,
            index=model_option.index(st.session_state["selected_model"]),
        )

        st.session_state["selected_model"] = model

        # 显示历史聊天记录
        existing_chats = get_history_chats(username)
        selected_chat = st.selectbox("选择聊天记录", [""] + existing_chats)

        if selected_chat and selected_chat != st.session_state.get("chat_name"):
            st.session_state["chat_name"] = selected_chat
            st.session_state["messages"] = load_data(username, selected_chat)
            st.session_state["preset_sent"] = False
            st.experimental_rerun()

        new_chat_name = st.text_input("新建聊天名称", "")

        cols = st.columns(3)
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

    if chosen_function == "实时天气查询":
        location = st.text_input("请输入查询地点")
        if st.button("查询天气"):
            prompt = f"请提供 {location} 的当前天气情况，包括温度、湿度、风速、风向和降雨概率等详细信息。接着，详细描述未来两天的天气预报，每天包括最高和最低气温、降雨概率、风速、风向、日出和日落时间。"
            st.session_state["messages"].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            stream_response(app_key, app_secret, st.session_state["messages"], username, prompt)
            save_data(username, st.session_state["chat_name"], st.session_state["messages"])

    elif chosen_function == "新闻搜索和摘要":
        keyword = st.text_input("请输入新闻关键词或类别")
        if st.button("搜索新闻"):
            prompt = f"请搜索关于 {keyword} 的最新新闻，并生成简短摘要。摘要应包括关键事件、重要人物、事件背景和可能的影响。请提供新闻的来源、发布日期和相关的链接以供进一步阅读。如果可能，请附上新闻的图片或视频。"
            st.session_state["messages"].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            stream_response(app_key, app_secret, st.session_state["messages"], username, prompt)
            save_data(username, st.session_state["chat_name"], st.session_state["messages"])

    elif chosen_function == "实时股票行情":
        stock_code = st.text_input("请输入股票代码或名称")
        if st.button("查询股票行情"):
            prompt = f"请提供 {stock_code} 的实时股票行情信息。包括当前价格、涨跌幅、成交量、开盘价、最高价和最低价等详细数据。请分析当前市场趋势，并提供相关的财务数据如市盈率、股息率、历史表现图表。如果可能，请提供分析师的预测和建议。"
            st.session_state["messages"].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            stream_response(app_key, app_secret, st.session_state["messages"], username, prompt)
            save_data(username, st.session_state["chat_name"], st.session_state["messages"])

    elif chosen_function == "旅游景点推荐":
        interest = st.text_input("请输入兴趣点或位置")
        if st.button("推荐景点"):
            prompt = f"请根据用户的兴趣 {interest} 推荐旅游景点。请提供每个景点的详细简介，包括景点特色、历史背景、开放时间、门票价格、最佳游览时间和推荐活动等信息。请附上景点的高清图片和地图，并提供游客评价和评分。如果可能，请提供景点附近的餐饮和住宿推荐。"
            st.session_state["messages"].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            stream_response(app_key, app_secret, st.session_state["messages"], username, prompt)
            save_data(username, st.session_state["chat_name"], st.session_state["messages"])

    elif chosen_function == "百科":
        topic = st.text_input("请输入查询主题")
        if st.button("搜索百科"):
            prompt = f"请提供关于 {topic} 的详细信息。内容应包括主题的背景、历史沿革、主要特点、当前发展状况和未来趋势。如果有相关的重要数据或事实，请详细列出。请附上相关的图片、图表和引用资料的链接，以便用户进一步阅读和参考。"
            st.session_state["messages"].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            stream_response(app_key, app_secret, st.session_state["messages"], username, prompt)
            save_data(username, st.session_state["chat_name"], st.session_state["messages"])

    # 显示历史消息
    for msg in st.session_state["messages"]:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("输入你的消息："):
        if prompt.strip():  # 确保输入内容非空
            st.session_state["messages"].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            if st.session_state["selected_model"] == "SkyChat-3.0":
                stream_response(app_key, app_secret, st.session_state["messages"], username, prompt)
            elif st.session_state["selected_model"] == "Baichuan4":
                baichuan_stream_response(BAICHUAN_API_KEY, "Baichuan4", st.session_state["messages"], username)
            else:
                yi_stream_response(YI_API_KEY, st.session_state["selected_model"], st.session_state["messages"], username)

            # 保存聊天记录
            if st.session_state["chat_name"]:
                save_data(username, st.session_state["chat_name"], st.session_state["messages"])

    handle_audio_input(app_key, app_secret, st.session_state["messages"], username)

if __name__ == "__main__":
    main(__login__obj)

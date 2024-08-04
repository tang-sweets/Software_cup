# import streamlit as st
# import threading
# import os
# import requests
# import json
# from tools.chat_histor import save_data
# from tools.audio_recognition import record_audio
#
# def upload_audio_for_transcription(api_key, file_path, url):
#     with open(file_path, 'rb') as audio_file:
#         response = requests.post(
#             url,
#             headers={
#                 'Authorization': f'Bearer {api_key}'
#             },
#             files={
#                 'file': audio_file
#             },
#             data={
#                 'model': 'whisper-1'
#             }
#         )
#         response.raise_for_status()  # 如果响应状态码不是200，抛出异常
#         return response.json()
#
# def handle_audio_input(api_key, chosen_model, message_history, username):
#     if 'is_recording' not in st.session_state:
#         st.session_state['is_recording'] = False
#
#     # 使用 Streamlit 的 columns 布局
#     col1, col2 = st.columns(2)
#
#     with col1:
#         if st.button("🎙️语音输入"):
#             if not st.session_state['is_recording']:
#                 st.session_state['is_recording'] = True
#                 st.info("聆听中。。。再次单击该按钮可停止。")
#                 thread = threading.Thread(target=record_audio, args=("static/wav/temp.wav", 30))
#                 thread.start()
#             else:
#                 st.session_state['is_recording'] = False
#                 st.info("语音输入完成。单击“📝”开始转录。")
#                 os.system("taskkill /im audiod.exe /f")
#
#     with col2:
#         if st.button("📝转录语音"):
#             st.info("正在转录，请稍候...")
#             try:
#                 # 上传音频文件并获取转录结果
#                 transcription_result = upload_audio_for_transcription(
#                     api_key,
#                     "static/wav/temp.wav",
#                     'https://api.bianxie.ai/v1/audio/transcriptions'
#                 )
#                 transcription = transcription_result.get("text", "")
#                 st.success("转录完成")
#                 st.chat_message("user").write(transcription)
#                 message_history.append({"role": "user", "content": transcription})
#
#                 # 处理转录后的消息
#                 chat_url = 'https://api.bianxieai.com/v1/chat/completions'
#                 headers = {
#                     'Content-Type': 'application/json',
#                     'Authorization': f'Bearer {api_key}'
#                 }
#
#                 data = {
#                     "model": chosen_model,
#                     "messages": message_history,
#                     "stream": True
#                 }
#
#                 # 发送请求并捕获异常
#                 try:
#                     response = requests.post(chat_url, json=data, headers=headers, stream=True)
#                     st.write("响应状态码:", response.status_code)
#                     st.write("响应内容:", response.text)
#                 except requests.exceptions.RequestException as e:
#                     st.error(f"Request failed: {e}")
#                     return
#
#                 if response.status_code == 200:
#                     assistant_response = st.empty()
#                     assistant_content = ""
#
#                     for chunk in response.iter_lines(decode_unicode=False):
#                         if chunk:
#                             chunk = chunk.decode('utf-8')
#                             if chunk.startswith("data: "):
#                                 chunk_data = chunk[len("data: "):].strip()
#                                 if chunk_data == "[DONE]":
#                                     break
#                                 try:
#                                     chunk_json = json.loads(chunk_data)
#                                     chunk_message = chunk_json['choices'][0]['delta']
#                                     if 'content' in chunk_message and chunk_message['content']:
#                                         assistant_content += chunk_message['content']
#                                         assistant_response.markdown(assistant_content)
#                                 except json.JSONDecodeError as e:
#                                     st.error(f"JSONDecodeError: {e}")
#                                     continue
#                     if assistant_content.strip():
#                         st.session_state["messages"].append({"role": "assistant", "content": assistant_content})
#                         st.experimental_rerun()
#                 else:
#                     st.error(f"Failed to fetch response from AI API: {response.status_code}, {response.text}")
#
#                 if st.session_state["chat_name"]:
#                     save_data(username, st.session_state["chat_name"], message_history)
#             except Exception as e:
#                 st.error(e)



import os
import threading
import streamlit as st
import requests
import json

from tools.audio_recognition import record_audio
from tools.chat_histor import save_data

def upload_audio_for_transcription(api_key, file_path, url, retries=3):
    for attempt in range(retries):
        try:
            with open(file_path, 'rb') as audio_file:
                response = requests.post(
                    url,
                    headers={'Authorization': f'Bearer {api_key}'},
                    files={'file': audio_file},
                    data={'model': 'whisper-1'}
                )
                response.raise_for_status()
                return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 502:
                st.warning(f"502 Bad Gateway Error: 重试 {attempt + 1}/{retries}")
                continue
            else:
                raise e
        except Exception as e:
            st.error(f"请求失败: {e}")
            raise e
    st.error("多次重试后仍然失败，请稍后再试。")
    return None

def handle_audio_input(api_key, chosen_model, message_history, username):
    if 'is_recording' not in st.session_state:
        st.session_state['is_recording'] = False

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🎙️语音输入"):
            if not st.session_state['is_recording']:
                st.session_state['is_recording'] = True
                st.info("聆听中。。。再次单击该按钮可停止。")
                thread = threading.Thread(target=record_audio, args=("static/wav/temp.wav", 30))
                thread.start()
            else:
                st.session_state['is_recording'] = False
                st.info("语音输入完成。单击“📝”开始转录。")
                os.system("taskkill /im audiod.exe /f")

    with col2:
        if st.button("📝转录语音"):
            st.info("正在转录，请稍候...")
            try:
                transcription_result = upload_audio_for_transcription(
                    api_key,
                    "static/wav/temp.wav",
                    'https://api.bianxieai.com/v1/audio/transcriptions'
                )
                if transcription_result:
                    transcription = transcription_result.get("text", "")
                    st.success("转录完成")
                    st.chat_message("user").write(transcription)
                    message_history.append({"role": "user", "content": transcription})

                    # 处理转录后的消息
                    chat_url = 'https://api.bianxieai.com/v1/chat/completions'
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {api_key}'
                    }

                    data = {
                        "model": chosen_model,
                        "messages": message_history,
                        "stream": True
                    }

                    try:
                        response = requests.post(chat_url, json=data, headers=headers, stream=True)
                        # st.write("请求数据:", json.dumps(data, indent=4))
                        # st.write("响应状态码:", response.status_code)
                        # st.write("响应内容:", response.text)
                    except requests.exceptions.RequestException as e:
                        st.error(f"请求失败: {e}")
                        return

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
                                        st.error(f"JSON解析错误: {e}")
                                        continue
                                    except IndexError as e:
                                        st.error(f"索引错误: {e}")
                                        continue
                        if assistant_content.strip():
                            st.session_state["messages"].append({"role": "assistant", "content": assistant_content})
                            st.experimental_rerun()
                    else:
                        st.error(f"获取AI API响应失败: {response.status_code}, {response.text}")

                    if st.session_state["chat_name"]:
                        save_data(username, st.session_state["chat_name"], message_history)
            except Exception as e:
                st.error(e)

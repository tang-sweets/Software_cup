import requests
import streamlit as st
from tools.chat_histor import save_data

def upload_and_extract_file(api_key, base_url, file, username, message_history):
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    files = {
        'file': (file.name, file, file.type)
    }

    # 上传文件
    response = requests.post(f"{base_url}/files", headers=headers, files=files)

    if response.status_code == 200:
        file_object = response.json()
        file_id = file_object['id']

        # 获取文件内容
        response = requests.get(f"{base_url}/files/{file_id}/content", headers=headers)
        if response.status_code == 200:
            file_content = response.text

            # 避免重复添加文件内容到消息历史
            if not any(msg['content'] == file_content for msg in message_history):
                message_history.append({"role": "system", "content": file_content, "is_file_content": True})
                save_data(username, st.session_state["chat_name"], message_history)
        else:
            st.error(f"Error: {response.status_code}, {response.text}")
    else:
        st.error(f"Error: {response.status_code}, {response.text}")

def handle_file_upload(api_key, base_url, username, message_history):
    uploaded_file = st.file_uploader("上传文件", type=["txt", "pdf", "doc", "docx", "png", "jpg", "jpeg"])
    if uploaded_file is not None:
        file_details = {"filename": uploaded_file.name, "filetype": uploaded_file.type, "filesize": uploaded_file.size}
        st.write(file_details)

        # 直接上传文件并提取内容
        if uploaded_file.type in ["text/plain", "application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "image/png", "image/jpeg"]:
            upload_and_extract_file(api_key, base_url, uploaded_file, username, message_history)
        else:
            st.error("不支持的文件类型")

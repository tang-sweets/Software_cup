import os
import torch
from PIL import Image
from torchvision import transforms
from torchvision.models import resnet18
import requests
import json
import streamlit as st
import threading
import sounddevice as sd
import wavio
from tools.chat_histor import save_data, load_data, get_history_chats, remove_data
import re

def strip_sup_tags(text):
    return re.sub(r'<sup>\d+</sup>', '', text)

# 设置 API Key
API_KEY = st.secrets["api"]["bianxie_key"]
YI_API_KEY = st.secrets["api"]["Yi_key"]

# 图像分类函数
def classify_image(class_names, image):
    num_classes = len(class_names)
    model = resnet18(pretrained=True)
    num_ftrs = model.fc.in_features
    model.fc = torch.nn.Linear(num_ftrs, num_classes)
    model.eval()

    # 加载预训练的模型权重
    checkpoint_path = './static/models/doctor.pth'
    if os.path.exists(checkpoint_path):
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        model.load_state_dict(checkpoint)
    else:
        st.error("预训练模型权重文件未找到。")

    # 图像预处理
    data_transform = transforms.Compose([
        transforms.Resize((224, 224)),  # 将图像调整为模型所需的大小
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    image = Image.open(image).convert("RGB")  # 将图像转换为RGB格式
    image = data_transform(image).unsqueeze(0)
    image = image.to('cpu')  # 将图像放到CPU上

    # 在模型上进行预测
    with torch.no_grad():
        outputs = model(image)
        probabilities = torch.nn.functional.softmax(outputs, dim=1)
        _, predicted = torch.max(outputs.data, 1)

    probabilities_dict = {class_names[i]: probabilities.tolist()[0][i] for i in range(num_classes)}

    result = {
        "class_index": predicted.item(),
        "class_name": class_names[predicted.item()],
        "probabilities": probabilities_dict
    }

    return result

# 语音录制和转录函数
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
                            # Remove <sup> tags
                            cleaned_content = strip_sup_tags(assistant_content)
                            assistant_response.markdown(cleaned_content)
                    except json.JSONDecodeError as e:
                        st.error(f"JSONDecodeError: {e}")
                        continue
        if assistant_content.strip():
            st.session_state["messages"].append({"role": "assistant", "content": strip_sup_tags(assistant_content)})
            if st.session_state["chat_name"]:
                save_data(username, st.session_state["chat_name"], message_history)
            st.experimental_rerun()
    else:
        st.error(f"Error: {response.status_code}, {response.text}")


def handle_audio_input(api_key, message_history, username):
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
            yi_stream_response(api_key, "yi-large-rag", message_history, username)
            save_data(username, st.session_state["chat_name"], message_history)
            st.experimental_rerun()
        except Exception as e:
            st.error(e)
            st.write(f"转录过程中出现错误: {e}")

def reset_classification_state():
    """重置分类相关状态"""
    st.session_state["image_classified"] = False
    st.session_state["classification_result"] = None
    st.session_state["uploaded_file"] = None

# 处理不同的任务
def handle_ai_task(prompt, task_type, messages, stream=True):
    api_key = st.secrets["api"]["Yi_key"]
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    task_prompts = {
        "皮肤病识别与治疗": "请根据上传的皮肤病图片，识别出皮肤病的类型，并提供详细的症状描述和治疗方法。",
        "推荐就诊科室": "根据用户描述的症状，推荐适合就诊的科室。",
        "疾病推断": "根据用户描述的症状，推断可能的疾病。如果信息不足，请继续询问用户以获取更多信息，直到能够做出合理的推断。",
    }

    data = {
        "model": "yi-large-rag",
        "messages": messages + [{"role": "user", "content": f"{task_prompts[task_type]} {prompt}"}],
        "temperature": 0.9,
        "top_p": 0.3,
        "stream": stream,
        "max_tokens": 4096  # 设置最大输出长度为4096
    }

    response = requests.post("https://api.lingyiwanwu.com/v1/chat/completions", headers=headers, json=data, stream=stream)

    if response.status_code == 200:
        if stream:
            assistant_content = ""
            assistant_response = st.empty()
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
            return assistant_content
        else:
            return response.json()['choices'][0]['message']['content']
    else:
        st.error(f"Error: {response.status_code}, {response.text}")
        return None

def main(__login__obj):
    """主函数，初始化应用程序并处理用户交互"""
    # 初始化会话状态
    if "chat_name" not in st.session_state:
        st.session_state["chat_name"] = None
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "image_classified" not in st.session_state:
        st.session_state["image_classified"] = False
    if "classification_result" not in st.session_state:
        st.session_state["classification_result"] = None
    if "uploaded_file" not in st.session_state:
        st.session_state["uploaded_file"] = None

    # 获取用户名
    username = __login__obj.get_username()

    st.title('健康助手')

    st.sidebar.title("选择功能")
    function_option = ["皮肤病识别与治疗", "推荐就诊科室", "疾病推断"]
    chosen_function = st.sidebar.selectbox("功能", function_option)

    # 侧边栏输入 API 密钥和设置
    with st.sidebar:
        st.write("选择模型:")
        st.session_state["current_model_Yi"] = "yi-large-rag"

        existing_chats = get_history_chats(username)
        selected_chat = st.selectbox("选择聊天记录", [""] + existing_chats)

        if selected_chat and selected_chat != st.session_state.get("chat_name"):
            st.session_state["chat_name"] = selected_chat
            st.session_state["messages"] = load_data(username, selected_chat)
            reset_classification_state()
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
                reset_classification_state()
                st.experimental_rerun()

        with cols[1]:
            if st.button("删除聊天") and selected_chat:
                remove_data(username, selected_chat)
                reset_classification_state()
                st.experimental_rerun()

    if st.session_state["last_chosen_function"] != chosen_function:
        st.session_state["messages"] = []
        st.session_state["last_chosen_function"] = chosen_function

    # 在功能“皮肤病识别与治疗”中更新详细提示
    if chosen_function == "皮肤病识别与治疗":
        uploaded_file = st.file_uploader("上传皮肤病图片", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            if uploaded_file != st.session_state["uploaded_file"]:
                reset_classification_state()
                st.session_state["uploaded_file"] = uploaded_file

            class_names = ['光化性角化病', '基底细胞癌', '皮肤纤维瘤', '黑色素瘤', '痣', '色素性良性角化病',
                           '脂溢性角化病', '鳞状细胞癌', '血管病变']  # 示例中文类别名称
            st.image(uploaded_file, caption="上传的皮肤病图片", use_column_width=True)
            if not st.session_state["image_classified"]:
                with st.spinner("识别中..."):
                    result = classify_image(class_names, uploaded_file)
                    st.session_state["classification_result"] = result
                    st.session_state["image_classified"] = True

                    diagnosis_message = f"""
    分类结果: {result['class_name']}。
    请提供详细信息，包括：
    - 这种皮肤病的常见症状
    - 可能的致病原因
    - 常见的治疗方法
    - 日常护理建议
    """
                    st.session_state["messages"].append({"role": "user", "content": diagnosis_message})
                    st.chat_message("user").write(diagnosis_message)
                    yi_stream_response(YI_API_KEY, "yi-large-rag", st.session_state["messages"], username)

        if st.session_state["classification_result"] is not None:
            result = st.session_state["classification_result"]
            st.write(f"分类结果: {result['class_name']}")
            st.write("概率分布:")
            st.json(result["probabilities"])

    # 在功能“推荐就诊科室”中更新详细提示
    elif chosen_function == "推荐就诊科室":
        symptoms = st.text_area("请输入您的症状描述", "详细描述您的症状...")
        if st.button("推荐科室"):
            if symptoms.strip():
                prompt = f"""
    用户描述的症状是：{symptoms}。
    请根据这些症状推荐用户应该去的就诊科室。请提供：
    - 一个或多个具体的科室名称（例如，皮肤科，内科，耳鼻喉科等）
    - 这些科室的职责范围
    - 为什么这些科室适合用户的症状
    - 如果症状涉及多个科室，请明确优先级或推荐顺序
    """
                st.session_state["messages"].append({"role": "user", "content": prompt})
                st.chat_message("user").write(prompt)
                yi_stream_response(YI_API_KEY, "yi-large-rag", st.session_state["messages"], username)
                save_data(username, st.session_state["chat_name"], st.session_state["messages"])

    # 在功能“疾病推断”中更新详细提示
    elif chosen_function == "疾病推断":
        symptoms = st.text_area("请输入您的症状描述", "详细描述您的症状...")
        if st.button("推断疾病"):
            if symptoms.strip():
                prompt = f"""
    用户描述的症状是：{symptoms}。
    请根据这些症状推断用户可能患的疾病。
    - 列出一个或多个可能的疾病
    - 对每个疾病进行详细解释，包括其主要症状、原因和可能的治疗方法
    - 如果信息不足，请继续询问用户以获取更多信息，直到能够做出合理的推断。
    """
                st.session_state["messages"].append({"role": "user", "content": prompt})
                st.chat_message("user").write(prompt)
                yi_stream_response(YI_API_KEY, "yi-large-rag", st.session_state["messages"], username)
                save_data(username, st.session_state["chat_name"], st.session_state["messages"])

    # 显示历史消息
    for msg in st.session_state["messages"]:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("输入你的消息："):
        if prompt.strip():  # 确保输入内容非空
            st.session_state["messages"].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            yi_stream_response(YI_API_KEY, "yi-large-rag", st.session_state["messages"], username)
            save_data(username, st.session_state["chat_name"], st.session_state["messages"])

    handle_audio_input(YI_API_KEY, st.session_state["messages"], username)

if __name__ == "__main__":
    main(__login__obj)


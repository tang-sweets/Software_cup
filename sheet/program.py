import json
import streamlit as st
import requests
from tools.chat_histor import get_history_chats, save_data, load_data, remove_data

ZHIPU_API_KEY = st.secrets["api"]["Zhipu_key"]
MODEL_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

def stream_response(api_key, message_history, username, model="codegeex-4"):
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": model,
            "messages": message_history,
            "stream": True,
            "max_tokens": 4096  # 设置最大输出长度为4096
        }

        response = requests.post(MODEL_API_URL, headers=headers, json=data, stream=True)

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
            st.error(f"Error: {response.status_code}, {response.text}")
    except Exception as e:
        st.error(f"请求过程中出现错误: {e}")

def run_code_in_sandbox(api_key, code):
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": "glm-4-alltools",
            "messages": [
                {"role": "system", "content": "你现在是一个代码执行助手。你只需执行用户提供的代码，并返回结果。"},
                {"role": "user", "content": code}
            ],
            "stream": True,
            "tools": [{"type": "code_interpreter", "sandbox": "auto"}],
            "max_tokens": 4096  # 设置最大输出长度为4096
        }

        response = requests.post(MODEL_API_URL, headers=headers, json=data, stream=True)

        if response.status_code == 200:
            result = ""
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
                                    result += chunk_message['content']
                        except json.JSONDecodeError as e:
                            st.error(f"JSONDecodeError: {e}")
                            continue
            st.markdown(result)
        else:
            st.error(f"Error: {response.status_code}, {response.text}")
    except Exception as e:
        st.error(f"请求过程中出现错误: {e}")

# 处理不同的任务
def handle_ai_task(prompt, task_type, messages, stream=True):
    api_key = st.secrets["api"]["Zhipu_key"]
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # 定义每个任务类型的具体描述，用于提示AI
    task_prompts = {
        "生成注释": "请为以下代码生成详细的注释：请确保注释清晰且易于理解，并覆盖代码中的关键逻辑和功能。详细风格：提供全面的注释，解释每一行代码的功能和逻辑。简洁风格：提供简短但有意义的注释，只解释主要功能和关键部分。标准风格：遵循一般的代码注释规范，提供适当的解释和注释。",
        "翻译成其他编程语言": "请将以下代码翻译成目标编程语言。请确保翻译后的代码功能与原始代码相同，并遵循目标语言的最佳实践。保留代码的所有功能和逻辑。使用目标语言的标准库和惯用法。确保代码易于理解和维护。",
        "代码生成": "根据以下描述生成相应的代码。请确保生成的代码符合描述的要求，代码应规范且易于理解。遵循编程最佳实践。确保代码具有良好的结构和可读性。如果描述中有特定要求或约束，请在生成的代码中体现出来。",
        "解决报错": "请帮我检查以下代码并解决出现的报错。请提供详细的解释，说明导致错误的原因以及如何修复。详细描述错误的原因。提供修复错误的具体步骤。如果需要，请解释相关的编程概念或机制。",
        "AI聊天帮助": "请详细回答以下问题，提供相关的解释和帮助。如果问题涉及编程或技术概念，请提供详细的解释和示例。如果问题涉及解决方案，请提供清晰的步骤和代码示例（如果适用）。尽可能全面和详细地回答问题，确保用户能够理解和解决问题。",
        "代码沙盒": "请在代码沙盒中运行以下代码，并返回执行结果。请确保代码在沙盒环境中安全运行。解释代码的执行结果。如果代码有错误或问题，请提供详细的诊断和修复建议。确保代码在沙盒环境中的执行是安全的，不会造成任何破坏或风险。"
    }

    data = {
        "model": "codegeex-4",
        "messages": messages + [{"role": "user", "content": f"{task_prompts[task_type]} {prompt}"}],
        "temperature": 0.9,
        "top_p": 0.3,
        "stream": stream,
        "max_tokens": 4096  # 设置最大输出长度为4096
    }

    response = requests.post(MODEL_API_URL, headers=headers, json=data, stream=stream)

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

# Streamlit 页面
def main(__login__obj):
    if "last_chosen_function" not in st.session_state:
        st.session_state["last_chosen_function"] = None

    st.sidebar.title("选择功能")
    function_option = ["生成注释", "翻译成其他编程语言", "代码生成", "解决报错", "AI聊天帮助", "代码沙盒"]
    chosen_function = st.sidebar.selectbox("功能", function_option)

    if st.session_state["last_chosen_function"] != chosen_function:
        st.session_state["messages"] = []
        st.session_state["last_chosen_function"] = chosen_function

    username = __login__obj.get_username()
    st.title("编程大师")

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

                preset_message = {
                    "role": "system",
                    "content": "你是一位耐心的编程老师，你叫CodeGeeX。你会为学生回答关于编程、代码、计算机方面的任何问题，提供格式规范、可以执行、准确安全的代码，并在必要时提供详细的解释。你会指出学生代码中的不足和优点，并给予评分。你也可以教学编程，帮助学生解决错误。请用中文回答。"
                }
                st.session_state["messages"].append(preset_message)
                st.session_state["preset_sent"] = True

                save_data(username, new_chat_name, st.session_state["messages"])
                st.experimental_rerun()

        with cols[1]:
            if st.button("删除聊天") and selected_chat:
                remove_data(username, selected_chat)
                st.experimental_rerun()

    if not st.session_state["preset_sent"]:
        preset_message = {
            "role": "system",
            "content": "你是一位耐心的编程老师，你叫CodeGeeX。你会为学生回答关于编程、代码、计算机方面的任何问题，提供格式规范、可以执行、准确安全的代码，并在必要时提供详细的解释。你会指出学生代码中的不足和优点，并给予评分。你也可以教学编程，帮助学生解决错误。请用中文回答。"
        }
        st.session_state["messages"].append(preset_message)
        st.session_state["preset_sent"] = True

    # 根据不同功能显示不同的输入框
    if chosen_function == "生成注释":
        code = st.text_area("请输入代码", "粘贴你的代码到这里...")
        style = st.selectbox("请选择注释风格", ["详细", "简洁", "标准"])
        prompt = f"""
我希望你为以下代码生成{style}风格的注释。请确保注释清晰且易于理解，并覆盖代码中的关键逻辑和功能。
- 详细风格：提供全面的注释，解释每一行代码的功能和逻辑。
- 简洁风格：提供简短但有意义的注释，只解释主要功能和关键部分。
- 标准风格：遵循一般的代码注释规范，提供适当的解释和注释。

代码：
{code}
"""

    elif chosen_function == "翻译成其他编程语言":
        code = st.text_area("请输入代码", "粘贴你的代码到这里...")
        common_languages = ["Python", "JavaScript", "Java", "C++", "Go", "Ruby", "其他"]
        target_language = st.selectbox("请选择目标编程语言", common_languages)
        if target_language == "其他":
            target_language = st.text_input("请输入目标编程语言", "例如：Python、JavaScript...")
        prompt = f"""
请将以下代码翻译成{target_language}语言。请确保翻译后的代码功能与原始代码相同，并遵循目标语言的最佳实践。
- 保留代码的所有功能和逻辑。
- 使用目标语言的标准库和惯用法。
- 确保代码易于理解和维护。

代码：
{code}
"""

    elif chosen_function == "代码生成":
        description = st.text_area("请输入代码描述", "描述你想生成的代码...")
        prompt = f"""
根据以下描述生成相应的代码。请确保生成的代码符合描述的要求，代码应规范且易于理解。
- 遵循编程最佳实践。
- 确保代码具有良好的结构和可读性。
- 如果描述中有特定要求或约束，请在生成的代码中体现出来。

描述：
{description}
"""

    elif chosen_function == "解决报错":
        code = st.text_area("请输入代码", "粘贴你的代码到这里...")
        error_message = st.text_area("请输入报错信息", "粘贴你的报错信息到这里...")
        prompt = f"""
请帮我检查以下代码并解决出现的报错。请提供详细的解释，说明导致错误的原因以及如何修复。
- 详细描述错误的原因。
- 提供修复错误的具体步骤。
- 如果需要，请解释相关的编程概念或机制。

代码：
{code}

报错信息：
{error_message}
"""

    elif chosen_function == "AI聊天帮助":
        question = st.text_area("请输入你的问题", "请详细描述你的问题...")
        prompt = f"""
请详细回答以下问题，提供相关的解释和帮助。
- 如果问题涉及编程或技术概念，请提供详细的解释和示例。
- 如果问题涉及解决方案，请提供清晰的步骤和代码示例（如果适用）。
- 尽可能全面和详细地回答问题，确保用户能够理解和解决问题。

问题：
{question}
"""

    elif chosen_function == "代码沙盒":
        code = st.text_area("请输入代码", "粘贴你的代码到这里...")
        prompt = code

    if st.button("生成"):
        with st.spinner("运行中..."):
            if chosen_function == "代码沙盒":
                result = run_code_in_sandbox(ZHIPU_API_KEY, prompt)
            else:
                result = handle_ai_task(prompt, chosen_function, message_history, stream=True)
            if result:
                st.session_state["messages"].append({"role": "assistant", "content": result})
                st.success(f"{chosen_function}生成成功！")
                st.experimental_rerun()
            else:
                st.error(f"{chosen_function}生成失败")

    # 显示聊天记录
    for msg in st.session_state["messages"]:
        st.chat_message(msg["role"]).write(msg["content"])

    # 底部聊天输入框
    if prompt := st.chat_input("输入您的消息:"):
        if not ZHIPU_API_KEY:
            st.warning("请在Streamlit密钥中配置您的API密钥")
            st.stop()

        with st.spinner("处理中..."):
            message_history.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            if st.session_state["chat_name"]:
                save_data(username, st.session_state["chat_name"], message_history)

            if st.session_state["use_sandbox"]:
                run_code_in_sandbox(ZHIPU_API_KEY, prompt)
            else:
                result = handle_ai_task(prompt, chosen_function, message_history, stream=True)
                if result:
                    st.session_state["messages"].append({"role": "assistant", "content": result})
                    st.experimental_rerun()

if __name__ == '__main__':
    main(__login__obj)

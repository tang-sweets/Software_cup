import json
import streamlit as st
import requests

from tools.chat_histor import get_history_chats, save_data, load_data, remove_data

MODEL_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ZHIPU_API_KEY = st.secrets["api"]["Zhipu_key"]


def stream_response(message_history, username):
    try:
        headers = {"Authorization": f"Bearer {ZHIPU_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "glm-4-alltools",
            "messages": message_history,
            "stream": True,
            "max_tokens": st.session_state["max_tokens"],
            "top_p": st.session_state["top_p"],
            "temperature": st.session_state["temperature"],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "example_function",
                        "description": "这是一个示例函数。",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "param1": {
                                    "description": "示例参数1",
                                    "type": "string"
                                },
                                "param2": {
                                    "description": "示例参数2",
                                    "type": "string"
                                }
                            },
                            "required": ["param1", "param2"]
                        }
                    }
                },
                {"type": "code_interpreter"},
                {"type": "web_browser"},
                {"type": "drawing_tool"}
            ]
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
                    save_data(username, st.session_state["chat_name"], message_history)
                st.experimental_rerun()
        else:
            st.error(f"Error: {response.status_code}, {response.text}")
    except Exception as e:
        st.error(f"请求过程中出现错误: {e}")


def main(__login__obj):
    username = __login__obj.get_username()

    st.title("学习AI助手")

    if "chat_name" not in st.session_state:
        st.session_state["chat_name"] = None
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "preset_sent" not in st.session_state:
        st.session_state["preset_sent"] = False

    message_history = st.session_state["messages"]

    st.sidebar.title("选择功能")
    function_option = ["AI写作", "AI翻译", "数学", "化学", "生物", "地理", "历史"]
    chosen_function = st.sidebar.selectbox("功能", function_option)

    with st.sidebar:
        st.title("聊天设置")


        existing_chats = get_history_chats(username)
        selected_chat = st.selectbox("选择聊天记录", [""] + existing_chats, index=0)

        if selected_chat and selected_chat != st.session_state.get("chat_name"):
            st.session_state["chat_name"] = selected_chat
            st.session_state["messages"] = load_data(username, selected_chat)
            st.experimental_rerun()

        new_chat_name = st.text_input("新建聊天名称", "")

        cols = st.columns(2)
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

    # st.write(f"当前使用的模型: GLM-4-AllTools")

    for msg in message_history:
        st.chat_message(msg["role"]).write(msg["content"])




    if chosen_function == "AI写作":
        st.title("AI写作")
        content_type = st.selectbox("选择内容类型", ["作文", "论文", "读后感"])
        stage = st.selectbox("选择阶段", ["学段", "小学", "初高中", "大学", "职场"])
        theme = st.text_input("输入主题", "")
        if theme and st.button("生成文章"):
            preset_message = {
                "role": "system",
                "content": f"请作为内容写作专家，帮我写一份文章，主题为{theme}，内容类型为{content_type}，要求作文文风符合{stage}阶段，字数在800字以上。"
            }
            message_history.append(preset_message)
            stream_response(message_history, username)

    elif chosen_function == "AI翻译":
        st.title("AI翻译")
        content_to_translate = st.text_area("输入需要翻译的内容")
        target_language = st.selectbox("选择翻译方向", ["英译汉", "汉译英", "汉译法", "法译汉", "汉译日", "日译汉"])
        if content_to_translate and st.button("翻译"):
            preset_message = {
                "role": "user",
                "content": f"请作为翻译专家，帮我翻译以下内容: {content_to_translate}，要求翻译方向为{target_language}。"
            }
            message_history.append(preset_message)
            stream_response(message_history, username)

    elif chosen_function == "数学":
        st.title("数学助手")
        math_task = st.selectbox("选择任务类型", ["解题", "公式推导", "概念解释"])
        math_problem = st.text_area("输入你的数学问题", "")
        if math_problem and st.button("解决问题"):
            if math_task == "解题":
                preset_message = {
                    "role": "user",
                    "content": f"请作为数学专家，帮我解答以下数学问题：{math_problem}"
                }
            elif math_task == "公式推导":
                preset_message = {
                    "role": "user",
                    "content": f"请作为数学专家，帮我推导以下公式：{math_problem}"
                }
            else:
                preset_message = {
                    "role": "user",
                    "content": f"请作为数学专家，帮我解释以下数学概念：{math_problem}"
                }
            message_history.append(preset_message)
            stream_response(message_history, username)

    elif chosen_function == "化学":
        st.title("化学助手")
        chemistry_task = st.selectbox("选择任务类型", ["化学反应", "实验解释", "概念解释"])
        if chemistry_task == "化学反应":
            reactants = st.text_input("输入反应物", "如：H2 + O2")
            conditions = st.text_input("输入反应条件", "如：加热")
            products = st.text_input("输入生成物", "如：H2O")
            chemistry_question = f"{reactants} 在 {conditions} 条件下生成 {products}"
        elif chemistry_task == "实验解释":
            chemistry_question = st.text_area("描述实验现象或问题", "")
        else:
            chemistry_question = st.text_area("输入化学概念或问题", "")

        if chemistry_question and st.button("解决问题"):
            if chemistry_task == "化学反应":
                preset_message = {
                    "role": "user",
                    "content": f"请作为化学专家，帮我解释以下化学反应：{chemistry_question}"
                }
            elif chemistry_task == "实验解释":
                preset_message = {
                    "role": "user",
                    "content": f"请作为化学专家，帮我解释以下实验现象：{chemistry_question}"
                }
            else:
                preset_message = {
                    "role": "user",
                    "content": f"请作为化学专家，帮我解释以下化学概念：{chemistry_question}"
                }
            message_history.append(preset_message)
            stream_response(message_history, username)

    elif chosen_function == "生物":
        st.title("生物助手")
        biology_task = st.selectbox("选择任务类型", ["遗传学", "生物过程", "概念解释"])
        if biology_task == "遗传学":
            trait = st.text_input("输入遗传性状", "如：红绿色盲")
            inheritance_pattern = st.text_input("输入遗传模式", "如：伴X隐性遗传")
            biology_question = f"{trait} 遗传模式为 {inheritance_pattern}"
        elif biology_task == "生物过程":
            biology_question = st.text_area("描述生物过程或问题", "如：光合作用的过程")
        else:
            biology_question = st.text_area("输入生物概念或问题", "")

        if biology_question and st.button("解决问题"):
            if biology_task == "遗传学":
                preset_message = {
                    "role": "user",
                    "content": f"请作为生物专家，帮我解释以下遗传学问题：{biology_question}"
                }
            elif biology_task == "生物过程":
                preset_message = {
                    "role": "user",
                    "content": f"请作为生物专家，帮我解释以下生物过程：{biology_question}"
                }
            else:
                preset_message = {
                    "role": "user",
                    "content": f"请作为生物专家，帮我解释以下生物概念：{biology_question}"
                }
            message_history.append(preset_message)
            stream_response(message_history, username)

    elif chosen_function == "地理":
        st.title("地理助手")
        geography_task = st.selectbox("选择任务类型", ["地理现象", "地理事件", "概念解释"])
        if geography_task == "地理现象":
            geography_question = st.text_area("描述地理现象或问题", "如：厄尔尼诺现象")
        elif geography_task == "地理事件":
            geography_question = st.text_area("描述地理事件或问题", "如：为什么日本多发地震")
        else:
            geography_question = st.text_area("输入地理概念或问题", "如：板块构造论")

        if geography_question and st.button("解决问题"):
            if geography_task == "地理现象":
                preset_message = {
                    "role": "user",
                    "content": f"请作为地理专家，帮我解释以下地理现象：{geography_question}"
                }
            elif geography_task == "地理事件":
                preset_message = {
                    "role": "user",
                    "content": f"请作为地理专家，帮我解释以下地理事件：{geography_question}"
                }
            else:
                preset_message = {
                    "role": "user",
                    "content": f"请作为地理专家，帮我解释以下地理概念：{geography_question}"
                }
            message_history.append(preset_message)
            stream_response(message_history, username)

    elif chosen_function == "历史":
        st.title("历史助手")
        history_task = st.selectbox("选择任务类型", ["历史事件", "人物传记", "概念解释"])
        if history_task == "历史事件":
            history_question = st.text_area("描述历史事件或问题", "如：长平之战")
        elif history_task == "人物传记":
            history_question = st.text_area("描述历史人物及其事迹", "如：秦始皇的生平事迹")
        else:
            history_question = st.text_area("输入历史概念或问题", "如：秦朝三权分立")

        if history_question and st.button("解决问题"):
            if history_task == "历史事件":
                preset_message = {
                    "role": "user",
                    "content": f"请作为历史专家，帮我解释以下历史事件：{history_question}"
                }
            elif history_task == "人物传记":
                preset_message = {
                    "role": "user",
                    "content": f"请作为历史专家，帮我撰写以下历史人物的传记：{history_question}"
                }
            else:
                preset_message = {
                    "role": "user",
                    "content": f"请作为历史专家，帮我解释以下历史概念：{history_question}"
                }
            message_history.append(preset_message)
            stream_response(message_history, username)

    else:
        if prompt := st.chat_input("输入您的消息:"):
            with st.spinner("处理中..."):
                message_history.append({"role": "user", "content": prompt})
                st.chat_message("user").write(prompt)

                if st.session_state["chat_name"]:
                    save_data(username, st.session_state["chat_name"], message_history)

                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {ZHIPU_API_KEY}'
                }
                data = {
                    "model": "glm-4-alltools",
                    "messages": message_history,
                    "max_tokens": st.session_state["max_tokens"],
                    "top_p": st.session_state["top_p"],
                    "temperature": st.session_state["temperature"],
                    "stream": True,
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "example_function",
                                "description": "这是一个示例函数。",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "param1": {
                                            "description": "示例参数1",
                                            "type": "string"
                                        },
                                        "param2": {
                                            "description": "示例参数2",
                                            "type": "string"
                                        }
                                    },
                                    "required": ["param1", "param2"]
                                }
                            }
                        },
                        {"type": "code_interpreter"},
                        {"type": "web_browser"},
                        {"type": "drawing_tool"}
                    ]
                }
                response = requests.post(MODEL_API_URL, json=data, headers=headers, stream=True)

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


if __name__ == "__main__":
    main(__login__obj)

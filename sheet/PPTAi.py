import hashlib
import hmac
import base64
import json
import time
import requests
import streamlit as st


class AIPPT:

    def __init__(self, APPId, APISecret, Text, create_model, theme, author, is_card_note, is_cover_img):
        self.APPid = APPId
        self.APISecret = APISecret
        self.text = Text
        self.create_model = create_model
        self.theme = theme
        self.author = author
        self.is_card_note = is_card_note
        self.is_cover_img = is_cover_img
        self.header = {}

    # 获取签名
    def get_signature(self, ts):
        try:
            auth = self.md5(self.APPid + str(ts))
            return self.hmac_sha1_encrypt(auth, self.APISecret)
        except Exception as e:
            st.error(f"Error: {e}")
            return None

    def hmac_sha1_encrypt(self, encrypt_text, encrypt_key):
        return base64.b64encode(
            hmac.new(encrypt_key.encode('utf-8'), encrypt_text.encode('utf-8'), hashlib.sha1).digest()).decode('utf-8')

    def md5(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    # 创建PPT生成任务
    def create_task(self):
        url = 'https://zwapi.xfyun.cn/api/aippt/create'
        timestamp = int(time.time())
        signature = self.get_signature(timestamp)
        body = self.getbody(self.text)

        headers = {
            "appId": self.APPid,
            "timestamp": str(timestamp),
            "signature": signature,
            "Content-Type": "application/json; charset=utf-8"
        }
        self.header = headers
        response = requests.post(url, json=body, headers=headers).text
        resp = json.loads(response)
        if resp['code'] == 0:
            return resp['data']['sid']
        else:
            st.error('创建PPT任务失败')
            return None

    # 构建请求body体
    def getbody(self, text):
        body = {
            "query": text,
            "create_model": self.create_model,
            "theme": self.theme,
            "author": self.author,
            "is_card_note": self.is_card_note,
            "is_cover_img": self.is_cover_img
        }
        return body

    # 轮询任务进度，返回完整响应信息
    def get_process(self, sid):
        if sid is not None:
            response = requests.get(f"https://zwapi.xfyun.cn/api/aippt/progress?sid={sid}", headers=self.header).text
            return response
        else:
            return None

    # 获取PPT，以下载连接形式返回
    def get_result(self):
        task_id = self.create_task()
        while True:
            response = self.get_process(task_id)
            if response:
                resp = json.loads(response)
                process = resp['data']['process']
                if process == 100:
                    return resp['data']['pptUrl']
            time.sleep(5)


# 新功能处理
def handle_ai_task(prompt, task_type, messages, stream=True):
    api_key = st.secrets["api"]["Yi_key"]
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    task_prompts = {
        "工作总结": "请根据以下内容生成一份详细的工作总结：",
        "方案设计": "请根据以下内容生成一个详细的方案设计：",
        "改写": "请作为内容专家，帮我将我的内容进行改写，要求内容逻辑清晰，表达分明。",
        "扩写": "请作为内容专家，帮我将我的内容进行扩写，要求内容逻辑清晰，表达分明。"
    }

    data = {
        "model": "yi-large",
        "messages": messages + [{"role": "user", "content": f"{task_prompts[task_type]} {prompt}"}],
        "temperature": 0.9,
        "top_p": 0.3,
        "stream": stream
    }

    response = requests.post(f"https://api.lingyiwanwu.com/v1/chat/completions", headers=headers, json=data,
                             stream=stream)

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
    function_option = ["PPT生成", "工作总结", "方案设计", "改写或扩写"]
    chosen_function = st.sidebar.selectbox("功能", function_option)

    if st.session_state["last_chosen_function"] != chosen_function:
        st.session_state["messages"] = []
        st.session_state["last_chosen_function"] = chosen_function

    if chosen_function == "PPT生成":
        st.title("AI PPT 生成应用")
        st.write("请输入描述文本，生成对应的PPT")

        text = st.text_area("描述文本", "软件杯演讲")

        st.sidebar.title("设置")
        create_model = st.sidebar.selectbox(
            "选择PPT生成类型",
            options=["auto", "topic", "text"],
            format_func=lambda x: "auto： 自动" if x == "auto" else "topic：话题生成（建议150字以内）" if x == "topic" else "text：文本生成，基于长文本生成",
            index=0
        )

        theme = st.sidebar.selectbox(
            "选择PPT生成主题",
            options=["auto", "purple", "green", "lightblue", "taupe", "blue", "telecomRed", "telecomGreen"],
            format_func=lambda x: {
                "auto": "auto：自动，随机主题",
                "purple": "purple：紫色主题",
                "green": "green：绿色主题",
                "lightblue": "lightblue：清逸天蓝",
                "taupe": "taupe：质感之境",
                "blue": "blue：星光夜影",
                "telecomRed": "telecomRed：炽热暖阳",
                "telecomGreen": "telecomGreen：幻翠奇旅"
            }.get(x, x),
            index=0
        )

        author = st.sidebar.text_input("PPT作者名", __login__obj.get_username())  # 使用登录对象的用户名

        is_card_note = st.sidebar.checkbox("是否生成PPT演讲备注", value=False)

        is_cover_img = st.sidebar.checkbox("是否生成封面图", value=False)

        if st.button("生成PPT"):
            with st.spinner("生成PPT中..."):
                APPId = "2133558c"
                APISecret = st.secrets["api"]["PPT_key"]
                ppt_generator = AIPPT(APPId, APISecret, text, create_model, theme, author, is_card_note, is_cover_img)
                ppt_url = ppt_generator.get_result()
                if ppt_url:
                    st.success("PPT生成成功！")
                    st.download_button(
                        label="下载PPT",
                        data=requests.get(ppt_url).content,
                        file_name="generated_ppt.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
                else:
                    st.error("生成PPT失败")
    else:
        st.title(f"AI {chosen_function}")
        st.write(f"请输入描述文本，用于生成{chosen_function}")

        # 根据功能显示不同的输入框
        if chosen_function == "工作总结":
            subject = st.text_input("请输入主题（必填）", "如增长团队年终总结")
            content = st.text_area("请输入工作内容", "如母婴产品直播、选品等")
            performance = st.text_area("请输入工作业绩", "如连续2季度销售冠军等")
            text = f"主题：{subject}\n工作内容：{content}\n工作业绩：{performance}"
        elif chosen_function == "方案设计":
            subject = st.text_input("请输入主题（必填）", "如市场推广方案设计")
            content = st.text_area("请输入方案细节", "如线上推广、线下活动等")
            text = f"主题：{subject}\n方案细节：{content}"
        elif chosen_function == "改写或扩写":
            subject = st.text_input("请输入主题（必填）", "粘贴需要处理内容到这里")
            content = st.text_area("请输入需要改写或扩写的文本", "如现有的文章内容")
            option = st.radio("选项（必选）", ["改写", "扩写"])
            text = f"主题：{subject}\n内容：{content}\n选项：{option}"

        if st.button("生成"):
            with st.spinner(f"生成{chosen_function}中..."):
                result = handle_ai_task(text, chosen_function if chosen_function != "改写或扩写" else option,
                                        st.session_state["messages"])
                if result:
                    st.session_state["messages"].append({"role": "assistant", "content": result})
                    st.success(f"{chosen_function}生成成功！")
                    st.experimental_rerun()
                else:
                    st.error(f"生成{chosen_function}失败")

        # 显示聊天记录
        for msg in st.session_state["messages"]:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])

        # 底部聊天输入框
        if prompt := st.chat_input("输入你的消息："):
            if prompt.strip():
                st.session_state["messages"].append({"role": "user", "content": prompt})
                with st.spinner("处理中..."):
                    result = handle_ai_task(prompt, chosen_function if chosen_function != "改写或扩写" else option,
                                            st.session_state["messages"], stream=True)
                    if result:
                        st.session_state["messages"].append({"role": "assistant", "content": result})
                        st.experimental_rerun()  # 重新加载页面，避免重复显示
                    else:
                        st.error("处理失败")


if __name__ == '__main__':
    main(__login__obj)

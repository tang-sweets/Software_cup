import hashlib
import hmac
import base64
import json
import time
import requests
import streamlit as st
from barfi import Block

def generate_image_agi_sky(api_key, api_secret, prompt):
    API_HOST = "api-maas.singularity-ai.com"
    url = f'https://{API_HOST}/sky-saas-image/api/v1/generate'
    app_key = api_key
    app_secret = api_secret
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
        "content": prompt
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        response_data = response.json()
        if response_data["code"] == 200 and "resp_data" in response_data:
            return response_data["resp_data"]["image_url"]
        else:
            raise Exception(f"API error: {response_data['code_msg']}")
    else:
        raise Exception(f"Request failed with status code: {response.status_code}, response: {response.text}")

def create_image_generation_block(api_key, api_secret):
    image_block = Block(name='图像生成')
    image_block.add_input(name='描述文本')
    image_block.add_output()

    def image_block_func(self):
        description_text = self.get_interface(name='描述文本')
        if not description_text:
            self.set_interface(name='Output 1', value="缺少描述文本")
            return

        try:
            image_url = generate_image_agi_sky(api_key, api_secret, description_text)
            self.set_interface(name='Output 1', value=image_url)
        except Exception as e:
            self.set_interface(name='Output 1', value=f"错误: {e}")

    image_block.add_compute(image_block_func)
    return image_block

class AIPPT:
    def __init__(self, APPId, APISecret, Text):
        self.APPid = APPId
        self.APISecret = APISecret
        self.text = Text
        self.header = {}

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

    def getbody(self, text):
        body = {
            "query": text,
            "create_model": "auto",
            "theme": "auto",
            "author": "自动生成",
            "is_card_note": False,
            "is_cover_img": False
        }
        return body

    def get_process(self, sid):
        if sid is not None:
            response = requests.get(f"https://zwapi.xfyun.cn/api/aippt/progress?sid={sid}", headers=self.header).text
            return response
        else:
            return None

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


def create_ppt_block(api_key):
    ppt_block = Block(name='PPT生成')
    ppt_block.add_input(name='描述文本')
    ppt_block.add_output()

    def ppt_block_func(self):
        description_text = self.get_interface(name='描述文本')

        if not description_text:
            self.set_interface(name='Output 1', value="缺少描述文本")
            return

        APPId = "2133558c"
        ppt_generator = AIPPT(APPId, api_key, description_text)
        ppt_url = ppt_generator.get_result()

        if ppt_url:
            self.set_interface(name='Output 1', value=ppt_url)
        else:
            self.set_interface(name='Output 1', value="生成PPT失败")

    ppt_block.add_compute(ppt_block_func)
    return ppt_block



def create_ai_response_block(api_key):
    ai_response = Block(name='deepseek_chat')
    ai_response.add_input()  # 第一输入
    ai_response.add_input()  # 第二输入
    ai_response.add_output()

    def ai_response_func(self):
        task_description = self.get_interface(name='Input 1') or "默认任务描述"
        input_text = self.get_interface(name='Input 2') or "默认输入内容"
        full_input = f"{task_description}: {input_text}"
        # 调用 Deepseek API 获取回应
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": full_input}]
            }
        )
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content']
            self.set_interface(name='Output 1', value=answer)
        else:
            self.set_interface(name='Output 1', value="AI 回应出错")
        time.sleep(1)  # 模拟等待时间

    ai_response.add_compute(ai_response_func)
    return ai_response

def create_yi_large_rag_block(api_key):
    yi_large_rag = Block(name='联网AI')
    yi_large_rag.add_input()  # 第一输入
    yi_large_rag.add_input()  # 第二输入
    yi_large_rag.add_output()

    def yi_large_rag_func(self):
        task_description = self.get_interface(name='Input 1') or "默认任务描述"
        input_text = self.get_interface(name='Input 2') or "默认输入内容"
        full_input = f"{task_description}: {input_text}"
        # 调用 Yi API 获取回应
        response = requests.post(
            "https://api.lingyiwanwu.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "yi-large-rag",
                "messages": [{"role": "user", "content": full_input}]
            }
        )
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content']
            self.set_interface(name='Output 1', value=answer)
        else:
            self.set_interface(name='Output 1', value="AI 回应出错")
        time.sleep(1)  # 模拟等待时间

    yi_large_rag.add_compute(yi_large_rag_func)
    return yi_large_rag

def create_yi_medium_200k_block(api_key):
    yi_medium_200k = Block(name='yi-medium-200k')
    yi_medium_200k.add_input()  # 第一输入
    yi_medium_200k.add_input()  # 第二输入
    yi_medium_200k.add_output()

    def yi_medium_200k_func(self):
        task_description = self.get_interface(name='Input 1') or "默认任务描述"
        input_text = self.get_interface(name='Input 2') or "默认输入内容"
        full_input = f"{task_description}: {input_text}"
        # 调用 Yi API 获取回应
        response = requests.post(
            "https://api.lingyiwanwu.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "yi-medium-200k",
                "messages": [{"role": "user", "content": full_input}]
            }
        )
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content']
            self.set_interface(name='Output 1', value=answer)
        else:
            self.set_interface(name='Output 1', value="AI 回应出错")
        time.sleep(1)  # 模拟等待时间

    yi_medium_200k.add_compute(yi_medium_200k_func)
    return yi_medium_200k

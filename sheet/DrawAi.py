import streamlit as st
import time
import requests
from datetime import datetime
from wsgiref.handlers import format_date_time
from time import mktime
import hashlib
import base64
import hmac
from urllib.parse import urlencode
import json
import requests
from barfi import Block
from io import BytesIO
from PIL import Image

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

class AssembleHeaderException(Exception):
    def __init__(self, msg):
        self.message = msg


class Url:
    def __init__(self, host, path, schema):
        self.host = host
        self.path = path
        self.schema = schema


# calculate sha256 and encode to base64
def sha256base64(data):
    sha256 = hashlib.sha256()
    sha256.update(data)
    digest = base64.b64encode(sha256.digest()).decode(encoding='utf-8')
    return digest


def parse_url(requset_url):
    stidx = requset_url.index("://")
    host = requset_url[stidx + 3:]
    schema = requset_url[:stidx + 3]
    edidx = host.index("/")
    if edidx <= 0:
        raise AssembleHeaderException("invalid request url:" + requset_url)
    path = host[edidx:]
    host = host[:edidx]
    u = Url(host, path, schema)
    return u


# 生成鉴权url
def assemble_ws_auth_url(requset_url, method="POST", api_key="", api_secret=""):
    u = parse_url(requset_url)
    host = u.host
    path = u.path
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    signature_origin = "host: {}\ndate: {}\n{} {} HTTP/1.1".format(host, date, method, path)
    signature_sha = hmac.new(api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                             digestmod=hashlib.sha256).digest()
    signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
    authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
        api_key, "hmac-sha256", "host date request-line", signature_sha)
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
    values = {
        "host": host,
        "date": date,
        "authorization": authorization
    }
    return requset_url + "?" + urlencode(values)


# 生成请求body体
def getBody(appid, text):
    body = {
        "header": {
            "app_id": appid,
            "uid": "123456789"
        },
        "parameter": {
            "chat": {
                "domain": "general",
                "temperature": 0.5,
                "max_tokens": 4096
            }
        },
        "payload": {
            "message": {
                "text": [
                    {
                        "role": "user",
                        "content": text
                    }
                ]
            }
        }
    }
    return body


# 发起请求并返回结果
def request_image(text, appid, apikey, apisecret):
    host = 'http://spark-api.cn-huabei-1.xf-yun.com/v2.1/tti'
    url = assemble_ws_auth_url(host, method='POST', api_key=apikey, api_secret=apisecret)
    content = getBody(appid, text)
    response = requests.post(url, json=content, headers={'content-type': "application/json"}).text
    return response


# AGI Sky-Saas-Image API 请求
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


# CogView 图像生成
def generate_image_cogview(api_key, model_name, prompt):
    url = "https://open.bigmodel.cn/api/paas/v4/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model_name,
        "prompt": prompt
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        response_data = response.json()
        if "data" in response_data and len(response_data["data"]) > 0:
            return response_data["data"][0]["url"]
        else:
            raise Exception("No image URL found in the response.")
    else:
        raise Exception(f"Request failed with status code: {response.status_code}, response: {response.text}")


# 将base64 的图片数据转换为Image对象
def base64_to_image(base64_data):
    img_data = base64.b64decode(base64_data)
    img = Image.open(BytesIO(img_data))
    return img


# 解析并显示图片
def parser_Message(message, width, height):
    data = json.loads(message)
    code = data['header']['code']
    if code != 0:
        st.error(f'请求错误: {code}, {data}')
    else:
        text = data["payload"]["choices"]["text"]
        imageContent = text[0]
        imageBase = imageContent["content"]
        img = base64_to_image(imageBase)

        # 调整图片大小
        img = img.resize((width, height))

        # 显示图片
        st.image(img, caption="生成的图片", use_column_width=True)

        # 添加下载按钮
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        st.download_button(
            label="下载图片",
            data=buffered.getvalue(),
            file_name="generated_image.jpg",
            mime="image/jpeg"
        )


# Streamlit 页面
def main(__login__obj):
    st.title("AI 画图应用")
    st.write("请输入描述文本，生成对应图片")

    desc = st.text_area("描述文本", "生成一张图：落霞与孤鹜齐飞，秋水共长天一色")

    st.sidebar.title("设置")
    width = st.sidebar.number_input("宽度", min_value=1, max_value=4096, value=512, step=1)
    height = st.sidebar.number_input("高度", min_value=1, max_value=4096, value=512, step=1)

    api_choice = st.sidebar.selectbox("选择 AI 模型", ["讯飞", "CogView", "AGI Sky-Saas-Image"])

    if st.button("生成图片"):
        with st.spinner("生成图片中..."):
            if api_choice == "CogView":
                API_KEY = st.secrets["api"]["Zhipu_key"]
                model_name = "cogview-3"
                try:
                    image_url = generate_image_cogview(API_KEY, model_name, desc)
                    st.image(image_url, caption=f"生成的图片 (使用 {api_choice})", use_column_width=True)

                    # 下载图片
                    response = requests.get(image_url)
                    img = Image.open(BytesIO(response.content))
                    buffered = BytesIO()
                    img.save(buffered, format="JPEG")
                    st.download_button(
                        label="下载图片",
                        data=buffered.getvalue(),
                        file_name="generated_image.jpg",
                        mime="image/jpeg"
                    )
                except Exception as e:
                    st.error(f"错误: {e}")
            elif api_choice == "AGI Sky-Saas-Image":
                APP_KEY = st.secrets["api"]["Tiangong_key"]
                APP_SECRET = st.secrets["api"]["Tiangong_secret"]
                try:
                    image_url = generate_image_agi_sky(APP_KEY, APP_SECRET, desc)
                    st.image(image_url, caption=f"生成的图片 (使用 {api_choice})", use_column_width=True)

                    # 下载图片
                    response = requests.get(image_url)
                    img = Image.open(BytesIO(response.content))
                    buffered = BytesIO()
                    img.save(buffered, format="JPEG")
                    st.download_button(
                        label="下载图片",
                        data=buffered.getvalue(),
                        file_name="generated_image.jpg",
                        mime="image/jpeg"
                    )
                except Exception as e:
                    st.error(f"错误: {e}")
            else:
                APPID = 'b728e2e5'
                APISecret = st.secrets["api"]["Draw_secret"]
                APIKEY = st.secrets["api"]["Draw_key"]
                res = request_image(desc, appid=APPID, apikey=APIKEY, apisecret=APISecret)
                parser_Message(res, width, height)
                st.caption(f"生成的图片 (使用 {api_choice})")


if __name__ == '__main__':
    main(__login__obj)

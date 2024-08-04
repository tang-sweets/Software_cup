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
from barfi import Block
from io import BytesIO
from PIL import Image
import os

# 图片生成函数
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

# 计算sha256并编码为base64
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

# 保存上传的文件
def save_uploaded_file(uploaded_file, save_dir="static/img"):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    file_path = os.path.join(save_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

# 将图片编码为base64
def encode_image_to_base64(file_path):
    with open(file_path, "rb") as image_file:
        img_str = base64.b64encode(image_file.read()).decode()
    return img_str

# 生成视频函数
def generate_video_cogvideox(api_key, prompt, image_base64=None):
    url = "https://open.bigmodel.cn/api/paas/v4/videos/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "cogvideox",
        "prompt": prompt,
    }
    if image_base64:
        payload["image_base64"] = image_base64

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        response_data = response.json()
        if "id" in response_data:
            return response_data["id"]
        else:
            raise Exception("No video ID found in the response.")
    else:
        raise Exception(f"Request failed with status code: {response.status_code}, response: {response.text}")

# 检查视频生成状态
# 检查视频生成状态
def check_video_status(api_key, video_id):
    url = f"https://open.bigmodel.cn/api/paas/v4/async-result/{video_id}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        response_data = response.json()
        if response_data["task_status"] == "SUCCESS":
            return response_data["video_result"][0]["url"]
        elif response_data["task_status"] == "FAIL":
            raise Exception("Video generation failed.")
        else:
            return None
    else:
        raise Exception(f"Request failed with status code: {response.status_code}, response: {response.text}")

# Streamlit 页面
def main(__login__obj):
    st.title("AI视觉创作")
    st.write("请输入描述文本，生成对应图片或视频")

    desc = st.text_area("描述文本", "请输入要生成的内容描述")

    st.sidebar.title("设置")
    generation_choice = st.sidebar.selectbox("选择生成类型", ["图片", "视频"])
    api_choice = st.sidebar.selectbox("选择 AI 模型", ["讯飞", "CogView", "AGI Sky-Saas-Image"]) if generation_choice == "图片" else None
    width = st.sidebar.number_input("宽度", min_value=1, max_value=4096, value=512, step=1) if generation_choice == "图片" else None
    height = st.sidebar.number_input("高度", min_value=1, max_value=4096, value=512, step=1) if generation_choice == "图片" else None
    uploaded_file = st.sidebar.file_uploader("上传图片 (可选)", type=["png", "jpg", "jpeg"]) if generation_choice == "视频" else None
    image_base64 = None

    if uploaded_file is not None:
        API_KEY = st.secrets["api"]["Zhipu_key"]
        try:
            with st.spinner("图片保存中..."):
                file_path = save_uploaded_file(uploaded_file)
            with st.spinner("图片编码中..."):
                image_base64 = encode_image_to_base64(file_path)
            st.sidebar.success("图片编码成功！")
        except Exception as e:
            st.sidebar.error(f"图片编码失败: {e}")

    if st.button(f"生成{generation_choice}"):
        if not desc:
            st.error("描述文本不能为空")
            return
        API_KEY = st.secrets["api"]["Zhipu_key"]
        if generation_choice == "图片":
            if api_choice == "CogView":
                model_name = "cogview-3"
                with st.spinner("生成图片中..."):
                    try:
                        image_url = generate_image_cogview(API_KEY, model_name, desc)
                        st.image(image_url, caption="生成的图片", use_column_width=True)

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
                with st.spinner("生成图片中..."):
                    try:
                        image_url = generate_image_agi_sky(APP_KEY, APP_SECRET, desc)
                        st.image(image_url, caption="生成的图片", use_column_width=True)

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
        elif generation_choice == "视频":
            with st.spinner("生成视频中..."):
                try:
                    video_id = generate_video_cogvideox(API_KEY, desc, image_base64)
                    generation_in_progress = True
                    while generation_in_progress:
                        video_url = check_video_status(API_KEY, video_id)
                        if video_url:
                            st.video(video_url)
                            st.success("视频生成成功!")

                            # 下载视频
                            response = requests.get(video_url)
                            video_bytes = response.content
                            st.download_button(
                                label="下载视频",
                                data=video_bytes,
                                file_name="generated_video.mp4",
                                mime="video/mp4"
                            )

                            generation_in_progress = False
                        else:
                            time.sleep(10)
                except Exception as e:
                    st.error(f"错误: {e}")

if __name__ == '__main__':
    main(__login__obj)


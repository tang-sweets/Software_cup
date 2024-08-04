from io import BytesIO

import requests
import streamlit as st
from PIL import Image
from barfi import st_barfi, Block, barfi_schemas
from tools.WorkAi import create_ai_response_block, create_yi_large_rag_block, create_yi_medium_200k_block, create_ppt_block, create_image_generation_block
import time

def main(__login__obj):
    username = __login__obj.get_username()

    # 创建用户输入块
    user_input = Block(name='用户输入')
    user_input.add_output()

    def user_input_func(self):
        input_value = st.text_input("请输入您的问题:", key="user_input")
        if st.button("发送", key="send"):
            self.set_interface(name='Output 1', value=input_value)
            time.sleep(1)  # 模拟等待时间

    user_input.add_compute(user_input_func)

    # 创建自定义功能块（没有输入）
    custom_function = Block(name='自定义功能')
    custom_function.add_output()

    def custom_function_func(self):
        custom_task = st.text_input("定义您希望AI执行的任务:", value="详细说明")
        if custom_task:
            self.set_interface(name='Output 1', value=custom_task)
            time.sleep(1)  # 模拟等待时间

    custom_function.add_compute(custom_function_func)

    # 创建合并块
    merge_block = Block(name='合并输入')
    merge_block.add_input()  # 第一输入
    merge_block.add_input()  # 第二输入
    merge_block.add_output()

    def merge_block_func(self):
        input_1 = self.get_interface(name='Input 1') or "默认输入1"
        input_2 = self.get_interface(name='Input 2') or "默认输入2"
        merged_output = f"{input_1}: {input_2}"
        self.set_interface(name='Output 1', value=merged_output)
        time.sleep(1)  # 模拟等待时间

    merge_block.add_compute(merge_block_func)

    # 调用 WorkAi.py 中的函数来创建 AI 回应块
    deepseek_api_key = st.secrets["api"]["Deepseek_key"]
    ai_response = create_ai_response_block(deepseek_api_key)

    # 调用 WorkAi.py 中的函数来创建 yi-large-rag 模型块
    yi_api_key = st.secrets["api"]["Yi_key"]
    yi_large_rag = create_yi_large_rag_block(yi_api_key)

    # 调用 WorkAi.py 中的函数来创建 yi-medium-200k 模型块
    yi_medium_200k = create_yi_medium_200k_block(yi_api_key)

    # 调用 WorkAi.py 中的函数来创建 PPT 生成块
    ppt_api_key = st.secrets["api"]["PPT_key"]
    ppt_block = create_ppt_block(ppt_api_key)

    # 调用 WorkAi.py 中的函数来创建图像生成块
    image_api_key = st.secrets["api"]["Tiangong_key"]
    image_api_secret = st.secrets["api"]["Tiangong_secret"]
    image_block = create_image_generation_block(image_api_key, image_api_secret)

    # 创建结果输出块
    result = Block(name='结果输出')
    result.add_input()

    def result_func(self):
        answer = self.get_interface(name='Input 1')
        if answer:
            with st.spinner('加载中...'):
                if answer.startswith("http"):
                    try:
                        # 尝试获取并显示图片
                        response = requests.get(answer)
                        response.raise_for_status()  # 检查请求是否成功
                        if 'image' in response.headers.get('Content-Type', ''):
                            img = Image.open(BytesIO(response.content))
                            st.image(img, caption="生成的图片", use_column_width=True)

                            buffered = BytesIO()
                            img.save(buffered, format="JPEG")
                            st.download_button(
                                label="下载图片",
                                data=buffered.getvalue(),
                                file_name="generated_image.jpg",
                                mime="image/jpeg"
                            )
                        elif answer.endswith(".ppt") or answer.endswith(".pptx"):
                            st.write(f"[点击这里下载PPT文件]({answer})")
                            st.download_button(
                                label="下载PPT",
                                data=response.content,
                                file_name="generated_presentation.pptx",
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                            )
                        else:
                            st.error(f"未知文件类型: {answer}")
                    except Exception as e:
                        st.error(f"无法加载文件: {str(e)}")
                else:
                    st.write(f"Bot: {answer}")
                time.sleep(1)  # 模拟等待时间

    result.add_compute(result_func)

    # 获取已保存的架构列表
    saved_schemas = barfi_schemas()

    # 在侧边栏选择一个架构进行加载
    with st.sidebar:
        selected_schema = st.selectbox("选择已保存的架构", saved_schemas)

    # 使用 st_barfi 构建图形界面
    compute_engine = st.checkbox('激活计算引擎', value=True)

    # 添加多个模型块
    blocks = [user_input, custom_function, merge_block, ai_response, yi_large_rag, yi_medium_200k, ppt_block, image_block, result]

    barfi_result = st_barfi(base_blocks=blocks, compute_engine=compute_engine, load_schema=selected_schema)

    # if barfi_result:
    #     st.write(barfi_result)

if __name__ == "__main__":
    main(__login__obj)

import streamlit as st
import requests
import json

# 设置 API Key 和 URL
API_KEY = st.secrets["api"]["Baichuan_key"]
API_URL = "https://api.baichuan-ai.com/v1/npc"
JSON_FILE_PATH = 'static/characters/characters.json'


# 定义一个函数来发送请求
def create_npc(data):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    response = requests.post(API_URL, data=json.dumps(data), headers=headers, timeout=60)
    return response


# 解析并显示角色信息
def display_response(response):
    if response.status_code == 200:
        st.success("角色创建成功！")
        st.json(response.json())
    else:
        st.error("角色创建失败")
        st.json(response.json())


# 将新角色信息写入到 JSON 文件
def write_to_json(file_path, character_name, character_id, character_description):
    with open(file_path, 'r+', encoding='utf-8') as file:
        # 加载现有的 JSON 数据
        data = json.load(file)
        # 更新自定义角色部分
        data['自定义角色'][character_name] = {
            "id": character_id,
            "description": character_description
        }
        # 将更新后的数据写回到文件
        file.seek(0)
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.truncate()


# Streamlit 页面
def main(__login__obj):
    st.title("角色创建")

    # 输入表单
    name = st.text_input(
        "角色名称",
        max_chars=20,
        help="例如：霁云"
    )
    basic_info = st.text_area(
        "角色基本信息",
        height=200,
        max_chars=2000,
        help=(
            "示例：\n"
            "[姓名]\n霁云\n\n"
            "[性别]\n男\n\n"
            "[物种]\n人类\n\n"
            "[年龄]\n22\n\n"
            "[工作]\n旅行者\n\n"
            "[昵称]\n霁云公子\n\n"
            "[生日]\n6月1\n\n"
            "[身高]\n178CM\n\n"
            "[体重]\n65KG\n\n"
            "[生肖]\n兔\n\n"
            "[星座]\n双子座\n\n"
            "[居住地]\n雾云城\n\n"
            "[恋爱状态]\n未知\n\n"
            "[爱好]\n旅行，磨练掌法\n\n"
            "[智商]\n高\n\n"
            "[情商]\n高\n\n"
            "[其他]\n霁云的武器是自己的手掌，技能有破空掌和掌心雷，破空掌是以惊人的速度和力量击打空气，形成一股强大的气流，能够击退敌人或将其击飞。掌心雷是通过集中内力于掌心，释放出强大的雷电攻击，对敌人造成毁灭性的伤害。\n\n"
            "[经典台词]\n 1. 我相信，只要坚持不懈地追寻，终有一天我会找到妹妹并带她回家！\n\n"
            "[口头禅]\n 2. 妹妹，你在哪里呢？\n\n"
            "[喜欢的事情 / 东西]\n 旅行，研究各种掌法与内力\n\n"
            "[不喜欢的事情 / 东西]\n 分离\n\n"
        )
    )
    opener = st.text_input(
        "开场白",
        max_chars=100,
        help="例如：(微笑着点点头)你好，确实很久不见了，近来过得如何?"
    )
    personality_list = st.multiselect(
        "角色性格设定",
        ["活泼", "乐观", "直爽", "幽默", "内敛", "腹黑", "自大", "傲娇", "高冷", "温和善良", "放荡不羁", "心思细腻",
         "豪迈潇洒", "不拘小节", "冷酷无情"],
        max_selections=5,
        help="例如：活泼, 乐观, 直爽"
    )
    personality_complement = st.text_input(
        "性格描述补充",
        max_chars=200,
        help="例如：急侠好义、刚猛不屈、敢作敢当"
    )
    biography = st.text_area(
        "角色经历",
        height=200,
        max_chars=2000,
        help=(
            "示例：\n"
            "霁云是雾云城霁家的大公子，从小就展现出在掌法上的天赋，在15岁的时候独自一人外出游历，磨练自己的掌法，在外游历期间被家人告知自己的妹妹霁雯意外失踪，霁云回到家中之后得知妹妹曾在自家的后山上遇见过一位老人，第二天妹妹就在后山失踪，霁云认为妹妹的失踪和这位老人有关系，但经过搜查之后并未找到这位老人，霁云觉得老人已经离开了雾云城，从此霁云便独自踏上了寻找妹妹的旅途。"
        )
    )
    relationships = st.text_input(
        "角色关系",
        max_chars=300,
        help="例如：妹妹：霁雯，从小一起长大，感情深厚，在自己的后山意外失踪。朋友：雾烟白，雾云城雾家二公子，自小和霁云相识，曾经在霁云寻找妹妹的过程中提供过帮助。"
    )
    user_nickname = st.text_input(
        "用户昵称",
        max_chars=20,
        help="例如：霁雯"
    )
    user_gender = st.selectbox(
        "用户性别",
        ["男人", "女人"],
        help="选择用户性别"
    )
    user_info = st.text_input(
        "用户信息",
        max_chars=100,
        help="例如：我是你的妹妹霁雯，和你从小一起长大，感情深厚"
    )
    model = st.selectbox(
        "角色绑定的模型",
        ["Baichuan-NPC-Turbo", "Baichuan-NPC-Lite"],
        help="选择角色绑定的模型"
    )
    temperature = st.slider(
        "回复多样性",
        0.01, 1.0, 0.8,
        help=(
            "角色对于某个问题回复的多样性。 数值越高，回复多样性越高；数值越低，回复内容更集中和确定\n"
        )
    )
    top_p = st.slider(
        "回复发散性",
        0.9, 1.0, 0.98,
        help=(
            "角色回复的发散性。 数值越高，回复的发散性越高，越不会完全遵循人设回复。建议该参数的值范围为0.9-1.0。此外，调整参数时，temperature和top_p，只调整其中一个。\n"
        )
    )
    max_tokens = st.slider(
        "max_tokens (指定生成内容的最大token数量)",
        min_value=1,
        max_value=512,
        value=512,
        help=(
            "角色单次回复时，最大生成的token数\n\n"

        )
    )

    # 点击按钮生成角色
    if st.button("创建角色"):
        data = {
            "name": name,
            "basic_info": basic_info,
            "opener": opener,
            "personality_list": personality_list,
            "personality_complement": personality_complement,
            "biography": biography,
            "relationships": relationships,
            "user_nickname": user_nickname,
            "user_gender": user_gender,
            "user_info": user_info,
            "model": model,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens
        }
        response = create_npc(data)
        display_response(response)

        if response.status_code == 200:
            npc_id = response.json().get("id")
            npc_description = data.get("personality_complement", "")
            write_to_json(JSON_FILE_PATH, name, npc_id, npc_description)


if __name__ == '__main__':
    main(__login__obj)

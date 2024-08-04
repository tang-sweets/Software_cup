import streamlit as st
from streamlit_login_auth_ui.widgets import __login__
# from sheets import DrawAi, Deepseek, KiMi, MultiModelAI, PPTAi, Yi, Tiangong, Baichuan, CopilotAi, Research
from streamlit_option_menu import option_menu
from sheet import a, CharactersAi, MultiModelAI, PPTAi, NetworkAi, ToolAi, Customize_character, Workflows, Knowledge, VideoGeneration, program, Doctor

# 从secrets.toml文件中读取邮箱账号和密码
sender_email = st.secrets["smtp"]["email"]
sender_password = st.secrets["smtp"]["password"]

# 实例化登录对象
__login__obj = __login__(sender_email=sender_email,
                         sender_password=sender_password,
                         company_name="Shims",
                         width=200, height=250,
                         logout_button_name='Logout', hide_menu_bool=False,
                         hide_footer_bool=False,
                         lottie_url='https://assets2.lottiefiles.com/packages/lf20_jcikwtux.json')


# 构建登录UI
LOGGED_IN = __login__obj.build_login_ui()
username = __login__obj.get_username()

if LOGGED_IN:
    st.sidebar.title(f"欢迎, {username}")

    with st.sidebar:
        selected = option_menu(
            menu_title=None,
            options=["===========基本功能===========", "多模态AI", "AI视觉创作", "角色模拟", "自定义创建模拟角色", "工作流", "===========平台应用===========", "职场AI工具", "编程助手", "健康助手", "智能联网助手",  "知识库助手", "学习Ai工具"],

            icons=["globe", "brush", "bar-chart", "fish", "lightbulb", "file", "file"],
            menu_icon="cast",
            default_index=0,
        )

    # 将 __login__obj 传递给各个模块
    if selected == "============基本功能============":
        a.main(__login__obj)
    elif selected == "多模态AI":
        MultiModelAI.main(__login__obj)
    elif selected == "AI视觉创作":
        VideoGeneration.main(__login__obj)
    elif selected == "角色模拟":
        CharactersAi.main(__login__obj)
    elif selected == "自定义创建模拟角色":
        Customize_character.main(__login__obj)
    elif selected == "工作流":
        Workflows.main(__login__obj)
    elif selected == "============平台应用============":
        a.main(__login__obj)
    elif selected == "编程助手":
        program.main(__login__obj)
    elif selected == "职场AI工具":
        PPTAi.main(__login__obj)
    elif selected == "健康助手":
        Doctor.main(__login__obj)
    elif selected == "智能联网助手":
        NetworkAi.main(__login__obj)
    elif selected == "学习Ai工具":
        ToolAi.main(__login__obj)
    elif selected == "知识库助手":
        Knowledge.main(__login__obj)

else:
    st.write("请登录以继续")

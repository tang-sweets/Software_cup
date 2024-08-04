import streamlit as st
import json
import os
from streamlit_lottie import st_lottie
from streamlit_option_menu import option_menu
from .utils import check_usr_pass
from .utils import load_lottieurl
from .utils import check_valid_name
from .utils import check_valid_email
from .utils import check_unique_email
from .utils import check_unique_usr
from .utils import register_new_usr
from .utils import check_email_exists
from .utils import generate_random_passwd
from .utils import send_passwd_in_email
from .utils import change_passwd
from .utils import check_current_passwd

class __login__:
    """
    为“登录/注册”页生成 UI。
    """
    def __init__(self, sender_email: str, sender_password: str, company_name: str, width, height, logout_button_name: str = 'Logout',
                 hide_menu_bool: bool = False, hide_footer_bool: bool = False,
                 lottie_url: str = "https://assets8.lottiefiles.com/packages/lf20_ktwnwv5m.json"):
        """
        Arguments:
        -----------
        1. self
        2. sender_email : 用于发送邮件的网易邮箱地址
        3. sender_password : 网易邮箱的授权码
        4. company_name : 这是将发送密码重置电子邮件的个人/组织的名称。
        5. width : 登录页面上动画的宽度。
        6. height : 登录页面上动画的高度。
        7. logout_button_name : 注销按钮名称。
        8. hide_menu_bool : 如果应隐藏流线型菜单，则传递 True。
        9. hide_footer_bool : 如果应隐藏“Made with streamlit”页脚，则传递 True。
        10. lottie_url : 您要在登录页面上使用的乐天动画。探索动画 - https://lottiefiles.com/featured
        """
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.company_name = company_name
        self.width = width
        self.height = height
        self.logout_button_name = logout_button_name
        self.hide_menu_bool = hide_menu_bool
        self.hide_footer_bool = hide_footer_bool
        self.lottie_url = lottie_url

        # 初始化 session_state 中的 cookie
        if 'cookies' not in st.session_state:
            st.session_state['cookies'] = {}

    def check_auth_json_file_exists(self, auth_filename: str) -> bool:
        """
        检查身份验证文件（存储用户信息的位置）是否已存在。
        """
        file_names = []
        for path in os.listdir('./'):
            if os.path.isfile(os.path.join('./', path)):
                file_names.append(path)

        present_files = []
        for file_name in file_names:
            if auth_filename in file_name:
                present_files.append(file_name)

            present_files = sorted(present_files)
            if len(present_files) > 0:
                return True
        return False

    def get_username(self):
        if st.session_state['LOGOUT_BUTTON_HIT'] == False:
            if '__streamlit_login_signup_ui_username__' in st.session_state['cookies']:
                username = st.session_state['cookies']['__streamlit_login_signup_ui_username__']
                return username

    def login_widget(self) -> None:
        """
        创建登录小部件，检查和设置session_state，对用户进行身份验证。
        """

        # Checks if session_state cookie exists.
        if st.session_state['LOGGED_IN'] == False:
            if st.session_state['LOGOUT_BUTTON_HIT'] == False:
                if '__streamlit_login_signup_ui_username__' in st.session_state['cookies']:
                    if st.session_state['cookies'][
                        '__streamlit_login_signup_ui_username__'] != '1c9a923f-fb21-4a91-b3f3-5f18e3f01182':
                        st.session_state['LOGGED_IN'] = True

        if st.session_state['LOGGED_IN'] == False:
            st.session_state['LOGOUT_BUTTON_HIT'] = False

            del_login = st.empty()
            with del_login.form("Login Form"):
                username = st.text_input("Username", placeholder='您的用户名')
                password = st.text_input("Password", placeholder='您的密码', type='password')

                st.markdown("###")
                login_submit_button = st.form_submit_button(label='登录')

                if login_submit_button:
                    authenticate_user_check = check_usr_pass(username, password)

                    if authenticate_user_check == False:
                        st.error("用户名或密码无效！")

                    else:
                        st.session_state['LOGGED_IN'] = True
                        st.session_state['cookies']['__streamlit_login_signup_ui_username__'] = username
                        del_login.empty()
                        st.experimental_rerun()

    def animation(self) -> None:
        """
        呈现 lottie 动画。
        """
        lottie_json = load_lottieurl(self.lottie_url)
        st_lottie(lottie_json, width=self.width, height=self.height)

    def sign_up_widget(self) -> None:
        """
        创建注册小组件，并以安全的方式将用户信息存储在_secret_auth_.json文件中。
        """
        with st.form("Sign Up Form"):
            name_sign_up = st.text_input("Name *", placeholder='请输入您的姓名')
            valid_name_check = check_valid_name(name_sign_up)

            email_sign_up = st.text_input("Email *", placeholder='请输入您的电子邮件')
            valid_email_check = check_valid_email(email_sign_up)
            unique_email_check = check_unique_email(email_sign_up)

            username_sign_up = st.text_input("Username *", placeholder='请输入您的用户名')
            unique_username_check = check_unique_usr(username_sign_up)

            password_sign_up = st.text_input("Password *", placeholder='创建强密码', type='password')

            st.markdown("###")
            sign_up_submit_button = st.form_submit_button(label='注册')

            if sign_up_submit_button:
                if valid_name_check == False:
                    st.error("请输入有效名称！")

                elif valid_email_check == False:
                    st.error("请输入有效的电子邮件！")

                elif unique_email_check == False:
                    st.error("电子邮件已存在！")

                elif unique_username_check == False:
                    st.error(f'对不起，用户名 {username_sign_up} 已经存在了！')

                elif unique_username_check == None:
                    st.error('请输入一个非空用户名！')

                if valid_name_check == True:
                    if valid_email_check == True:
                        if unique_email_check == True:
                            if unique_username_check == True:
                                register_new_usr(name_sign_up, email_sign_up, username_sign_up, password_sign_up)
                                st.success("注册成功！")

    def forgot_password(self) -> None:
        """
        创建忘记密码小组件，并在用户身份验证（电子邮件）后触发向用户发送电子邮件
        包含随机密码。
        """
        with st.form("Forgot Password Form"):
            email_forgot_passwd = st.text_input("Email", placeholder='请输入您的电子邮件')
            email_exists_check, username_forgot_passwd = check_email_exists(email_forgot_passwd)

            st.markdown("###")
            forgot_passwd_submit_button = st.form_submit_button(label='获取密码')

            if forgot_passwd_submit_button:
                if email_exists_check == False:
                    st.error("电子邮件ID未在我们这里注册！")

                if email_exists_check == True:
                    random_password = generate_random_passwd()
                    send_passwd_in_email(self.sender_email, self.sender_password, username_forgot_passwd,
                                         email_forgot_passwd,
                                         self.company_name, random_password)

                    change_passwd(email_forgot_passwd, random_password)
                    st.success("安全密码发送成功！")

    def reset_password(self) -> None:
        """
        Creates the reset password widget and after user authentication (email and the password shared over that email),
        resets the password and updates the same in the _secret_auth_.json file.
        """
        with st.form("Reset Password Form"):
            email_reset_passwd = st.text_input("Email", placeholder='请输入您的电子邮件')
            email_exists_check, username_reset_passwd = check_email_exists(email_reset_passwd)

            current_passwd = st.text_input("Temporary Password",
                                           placeholder='请在电子邮件中输入您收到的密码')
            current_passwd_check = check_current_passwd(email_reset_passwd, current_passwd)

            new_passwd = st.text_input("New Password", placeholder='请输入新的强密码',
                                       type='password')

            new_passwd_1 = st.text_input("Re - Enter New Password", placeholder='请重新输入新密码',
                                         type='password')

            st.markdown("###")
            reset_passwd_submit_button = st.form_submit_button(label='重置密码')

            if reset_passwd_submit_button:
                if email_exists_check == False:
                    st.error("电子邮件不存在！")

                elif current_passwd_check == False:
                    st.error("临时密码不正确！")

                elif new_passwd != new_passwd_1:
                    st.error("密码不匹配！")

                if email_exists_check == True:
                    if current_passwd_check == True:
                        change_passwd(email_reset_passwd, new_passwd)
                        st.success("密码重置成功！")

    def logout_widget(self) -> None:
        """
        仅当用户登录时，才会在边栏中创建注销小组件。
        """
        if st.session_state['LOGGED_IN'] == True:
            del_logout = st.sidebar.empty()
            del_logout.markdown("#")
            logout_click_check = del_logout.button(self.logout_button_name)

            if logout_click_check == True:
                st.session_state['LOGOUT_BUTTON_HIT'] = True
                st.session_state['LOGGED_IN'] = False
                st.session_state['cookies']['__streamlit_login_signup_ui_username__'] = '1c9a923f-fb21-4a91-b3f3-5f18e3f01182'
                del_logout.empty()
                st.experimental_rerun()

    def nav_sidebar(self):
        """
        创建侧面导航栏
        """
        main_page_sidebar = st.sidebar.empty()
        with main_page_sidebar:
            selected_option = option_menu(
                menu_title='Navigation',
                menu_icon='list-columns-reverse',
                icons=['box-arrow-in-right', 'person-plus', 'x-circle', 'arrow-counterclockwise'],
                options=['Login', 'Create Account', 'Forgot Password?', 'Reset Password'],
                styles={
                    "container": {"padding": "5px"},
                    "nav-link": {"font-size": "14px", "text-align": "left", "margin": "0px"}})
        return main_page_sidebar, selected_option

    def hide_menu(self) -> None:
        """
        隐藏位于右上角的流线型菜单。
        """
        st.markdown(""" <style>
        #MainMenu {visibility: hidden;}
        </style> """, unsafe_allow_html=True)

    def hide_footer(self) -> None:
        """
        隐藏“Made with streamlit”页脚。
        """
        st.markdown(""" <style>
        footer {visibility: hidden;}
        </style> """, unsafe_allow_html=True)

    def build_login_ui(self):
        """
        将所有内容整合在一起，调用重要功能。
        """
        if 'LOGGED_IN' not in st.session_state:
            st.session_state['LOGGED_IN'] = False

        if 'LOGOUT_BUTTON_HIT' not in st.session_state:
            st.session_state['LOGOUT_BUTTON_HIT'] = False

        auth_json_exists_bool = self.check_auth_json_file_exists('_secret_auth_.json')

        if auth_json_exists_bool == False:
            with open("_secret_auth_.json", "w") as auth_json:
                json.dump([], auth_json)

        main_page_sidebar, selected_option = self.nav_sidebar()

        if selected_option == 'Login':
            c1, c2 = st.columns([7, 3])
            with c1:
                self.login_widget()
            with c2:
                if st.session_state['LOGGED_IN'] == False:
                    self.animation()

        if selected_option == 'Create Account':
            self.sign_up_widget()

        if selected_option == 'Forgot Password?':
            self.forgot_password()

        if selected_option == 'Reset Password':
            self.reset_password()

        self.logout_widget()

        if st.session_state['LOGGED_IN'] == True:
            main_page_sidebar.empty()

        if self.hide_menu_bool == True:
            self.hide_menu()

        if self.hide_footer_bool == True:
            self.hide_footer()

        return st.session_state['LOGGED_IN']

# Author: Gauri Prabhakar
# GitHub: https://github.com/GauriSP10/streamlit_login_auth_ui

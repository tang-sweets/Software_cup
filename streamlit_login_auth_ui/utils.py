import re
import json
import os
import random
import string
import secrets
from argon2 import PasswordHasher
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

ph = PasswordHasher()

def check_usr_pass(username: str, password: str) -> bool:
    """
    对用户名和密码进行身份验证。
    """
    with open("_secret_auth_.json", "r") as auth_json:
        authorized_user_data = json.load(auth_json)

    for registered_user in authorized_user_data:
        if registered_user['username'] == username:
            try:
                passwd_verification_bool = ph.verify(registered_user['password'], password)
                if passwd_verification_bool:
                    return True
            except:
                pass
    return False

def load_lottieurl(url: str) -> str:
    """
    使用 URL 获取 lottie 动画。
    """
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        pass

def check_valid_name(name_sign_up: str) -> bool:
    """
    检查用户在创建帐户时是否输入了有效名称。
    """
    name_regex = (r'^[A-Za-z_][A-Za-z0-9_]*')

    if re.search(name_regex, name_sign_up):
        return True
    return False

def check_valid_email(email_sign_up: str) -> bool:
    """
    检查用户在创建帐户时是否输入了有效的电子邮件。
    """
    regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')

    if re.fullmatch(regex, email_sign_up):
        return True
    return False

def check_unique_email(email_sign_up: str) -> bool:
    """
    检查电子邮件是否已存在（因为电子邮件必须是唯一的）。
    """
    authorized_user_data_master = list()
    with open("_secret_auth_.json", "r") as auth_json:
        authorized_users_data = json.load(auth_json)

        for user in authorized_users_data:
            authorized_user_data_master.append(user['email'])

    if email_sign_up in authorized_user_data_master:
        return False
    return True

def non_empty_str_check(username_sign_up: str) -> bool:
    """
    检查非空字符串。
    """
    empty_count = 0
    for i in username_sign_up:
        if i == ' ':
            empty_count = empty_count + 1
            if empty_count == len(username_sign_up):
                return False

    if not username_sign_up:
        return False
    return True

def check_unique_usr(username_sign_up: str):
    """
    检查用户名是否已经存在（因为用户名需要是唯一的），
    还检查非 - 空用户名。
    """
    authorized_user_data_master = list()
    with open("_secret_auth_.json", "r") as auth_json:
        authorized_users_data = json.load(auth_json)

        for user in authorized_users_data:
            authorized_user_data_master.append(user['username'])

    if username_sign_up in authorized_user_data_master:
        return False

    non_empty_check = non_empty_str_check(username_sign_up)

    if not non_empty_check:
        return None
    return True

def register_new_usr(name_sign_up: str, email_sign_up: str, username_sign_up: str, password_sign_up: str) -> None:
    """
    将新用户的信息保存在_secret_auth.json文件中。
    """
    new_usr_data = {'username': username_sign_up, 'name': name_sign_up, 'email': email_sign_up,
                    'password': ph.hash(password_sign_up)}

    with open("_secret_auth_.json", "r") as auth_json:
        authorized_user_data = json.load(auth_json)

    with open("_secret_auth_.json", "w") as auth_json_write:
        authorized_user_data.append(new_usr_data)
        json.dump(authorized_user_data, auth_json_write)

    # 为新用户创建聊天目录
    user_chat_dir = f"chats/{username_sign_up}"
    os.makedirs(user_chat_dir, exist_ok=True)
    print(f"用户 {username_sign_up} 注册成功，并创建了聊天目录。")

def check_username_exists(user_name: str) -> bool:
    """
    检查_secret_auth.json文件中是否存在用户名。
    """
    authorized_user_data_master = list()
    with open("_secret_auth_.json", "r") as auth_json:
        authorized_users_data = json.load(auth_json)

        for user in authorized_users_data:
            authorized_user_data_master.append(user['username'])

    if user_name in authorized_user_data_master:
        return True
    return False

def check_email_exists(email_forgot_passwd: str):
    """
    检查输入的电子邮件是否存在于_secret_auth.json文件中。
    """
    with open("_secret_auth_.json", "r") as auth_json:
        authorized_users_data = json.load(auth_json)

        for user in authorized_users_data:
            if user['email'] == email_forgot_passwd:
                return True, user['username']
    return False, None

# def generate_random_passwd() -> str:
#     """
#     生成要通过电子邮件发送的随机密码。
#     """
#     password_length = 10
#     return secrets.token_urlsafe(password_length)

def generate_random_passwd() -> str:
    """
    生成要通过电子邮件发送的随机密码。
    """
    password_length = 6
    chars = string.ascii_letters + string.digits
    simple_passwd = ''.join(random.choice(chars) for i in range(password_length))
    return simple_passwd

def send_email_netease(sender_email, sender_password, receiver_email, subject, body):
    """
    使用网易邮箱发送电子邮件。
    """
    # 创建一个多部分的邮件消息对象
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email

    # 创建邮件正文
    part = MIMEText(body, "plain")
    message.attach(part)

    # 连接到网易 163 邮箱的 SMTP 服务器
    with smtplib.SMTP_SSL("smtp.163.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, message.as_string())

def send_passwd_in_email(sender_email, sender_password, username_forgot_passwd, email_forgot_passwd, company_name, random_password):
    """
    触发向用户发送包含随机生成的密码的电子邮件。
    """
    subject = company_name + ": Login Password!"
    body = f"Hi! {username_forgot_passwd},\n\n您的临时登录密码是: {random_password}\n\n出于安全原因，请尽早重置密码。"
    send_email_netease(sender_email, sender_password, email_forgot_passwd, subject, body)

def change_passwd(email_: str, random_password: str) -> None:
    """
    将旧密码替换为新生成的密码。
    """
    with open("_secret_auth_.json", "r") as auth_json:
        authorized_users_data = json.load(auth_json)

    with open("_secret_auth_.json", "w") as auth_json_:
        for user in authorized_users_data:
            if user['email'] == email_:
                user['password'] = ph.hash(random_password)
        json.dump(authorized_users_data, auth_json_)

def check_current_passwd(email_reset_passwd: str, current_passwd: str) -> bool:
    """
    在以下情况下对针对用户名输入的密码进行身份验证
    重置密码。
    """
    with open("_secret_auth_.json", "r") as auth_json:
        authorized_users_data = json.load(auth_json)

        for user in authorized_users_data:
            if user['email'] == email_reset_passwd:
                try:
                    if ph.verify(user['password'], current_passwd):
                        return True
                except:
                    pass
    return False

# Author: Gauri Prabhakar
# GitHub: https://github.com/GauriSP10/streamlit_login_auth_ui

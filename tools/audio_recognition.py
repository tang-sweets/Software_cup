import streamlit as st
import sounddevice as sd
import wavio
import requests

# 在这里设置您的 API Key
API_KEY = st.secrets["api"]["bianxie_key"],

def record_audio(file_path, duration=30, fs=44100):
    """录音函数，将录音保存到指定文件路径"""
    print("聆听中...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=2)
    sd.wait()  # 等待录音结束
    wavio.write(file_path, recording, fs, sampwidth=2)
    print("听取完成")

def transcribe_audio(file_path):
    """语音识别函数，将音频文件上传并返回识别文本"""
    url = 'https://api.bianxieai.com/v1/audio/transcriptions'
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    files = {
        "file": ("audio.wav", open(file_path, "rb")),
        "model": (None, "whisper-1")
    }

    response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        return response.json().get('text', '')
    else:
        raise Exception(f"Failed to get translation: {response.status_code} - {response.text}")

def record_and_transcribe(file_path="temp.wav", duration=30):
    """综合录音和语音识别功能"""
    record_audio(file_path, duration)
    transcription = transcribe_audio(file_path)
    return transcription

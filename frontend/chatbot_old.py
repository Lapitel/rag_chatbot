a='''
import os
import sys
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import streamlit as st
from streamlit_chat import message
import requests
import uuid
import base64
import time
from config.config import ConfigLoader
config = ConfigLoader()

# header
st.header("LUXIA-ON")
#st.markdown("[Saltlux](https://www.saltlux.com/)")

# 함수 선언부
def clear_text():
    st.session_state['temp'] = st.session_state["text"]
    st.session_state["text"] = ""

def getFileList():
    subfolders = [f.path for f in os.scandir(parent_dir + '/upload_files') if f.is_dir()]
    return [subfolder.split("upload_files", 1)[-1].lstrip(os.path.sep) for subfolder in subfolders]

def options_select():
    if "selected_options" in st.session_state:
        if '모두 선택' in st.session_state["selected_options"]:
            st.session_state["selected_options"] = ['모두 선택']
            st.session_state["max_selections"] = 1
        else:
            st.session_state["max_selections"] = len(available_options)-1

def make_json(filenames, encoded_data, question, session_id):
    return {
    "input": {
    "uploaded_filenames": filenames,
    "file": encoded_data,
    "question": question
    },
    "config": {
        "configurable": {
        "session_id": session_id
        }
    },
    "kwargs": {}
    }

# session 초기화
available_options = ['모두 선택'] + getFileList()
if "max_selections" not in st.session_state:
    st.session_state["max_selections"] = len(available_options)

if 'session_id' not in st.session_state:
    #st.session_state['session_id'] = str(uuid.uuid4().hex)
    st.session_state['session_id'] = requests.get("http://211.109.9.152:7333/generate_token").json()['token']

if "messages" not in st.session_state:
    st.session_state.messages = []


# sidebar 설정: 파일 업로드 및 목록에서 파일 선택
with st.sidebar:
    st.markdown("## Upload a PDF")
    file_uploader = st.file_uploader("Upload a PDF",accept_multiple_files=False, type="pdf")

    if file_uploader is not None:
        file_contents = file_uploader.read()
        encoded_data = base64.b64encode(file_contents).decode('utf-8')
        filename = file_uploader.name.strip()
    else:
        encoded_data, filename = '', ''
        
    st.multiselect(
        label = "Select an Option",
        options=available_options,
        key="selected_options",
        max_selections=st.session_state['max_selections'],
        on_change=options_select,
        format_func=lambda x: "모두 선택" if x == '모두 선택' else str(x),
    ) 

    st.write(
        available_options[1:] if st.session_state["max_selections"] == 1 else st.session_state["selected_options"]
    )

selected_files = available_options[1:] if st.session_state["max_selections"] == 1 else st.session_state["selected_options"]

############
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("질문을 입력해주세요"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        try:
            response = requests.post("http://211.109.9.152:7333/invoke",
                                json=make_json(selected_files, encoded_data, user_input, st.session_state['session_id']),
                                headers={
                                    'accept': 'application/json',
                                    'Content-Type': 'application/json'
                                    }
                                )
        except requests.exceptions.RequestException as error:
            try:
                response = requests.post("http://localhost:7333/invoke",
                                json=make_json(selected_files, encoded_data, user_input, st.session_state['session_id']),
                                headers={
                                    'accept': 'application/json',
                                    'Content-Type': 'application/json'
                                    }
                                )
            except requests.exceptions.RequestException:
                raise Exception(error)

        print(make_json(selected_files, encoded_data, user_input, st.session_state['session_id']))
        print(user_input)
        print(response.json())
        print()
        result = response.json()['output']['content']
        for chunk in result.split():
            full_response += chunk + " "
            time.sleep(0.05)

            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
        
    st.session_state.messages.append({"role": "assistant", "content": full_response})
'''
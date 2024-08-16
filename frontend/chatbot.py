import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import json
import streamlit as st
import requests
import asyncio
import aiohttp

BACKEND_URL = "http://localhost:8080"

# session_state init
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]
if "files" not in st.session_state:
    st.session_state["files"] = []
if "uploaded_file_ids" not in st.session_state:
    st.session_state["uploaded_file_ids"] = []

# sidebar section
with st.sidebar:
    # openai api key
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    
    # file upload
    uploaded_files = st.file_uploader(
        "Choose a PDF file", accept_multiple_files=True
    )
    # process file upload
    if uploaded_files:
        upload_msg_layer = st.empty()
        upload_msg_layer.info("Uploading files...")

        async def upload_file(file):
            async def async_post(session, url, filename, data=None, json=None):
                async with session.post(url, data=data, json=json) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        st.error(f"Failed to upload {filename}")
            
            async with aiohttp.ClientSession() as session:
                # file upload
                file_data = file.getvalue()
                upload_form = aiohttp.FormData()
                upload_form.add_field(
                    'file',
                    file_data,
                    filename=file.name
                )
                file_info = await async_post(session, url=f"{BACKEND_URL}/file", filename=file.name, data=upload_form)
                if file_info:
                    print(f"if after")
                    # convert txt -> dict
                    file_info = json.loads(file_info)
                    print(f"json after")
                    # file indexing
                    file_info = await async_post(session, url=f"{BACKEND_URL}/indexing", filename=file.name, json=file_info)
                    print(f"async_post after")
                    if file_info:
                        st.session_state["uploaded_file_ids"].append(json.loads(file_info))
        
        # 비동기 파일 업로드 실행
        async def async_run(files):
            await asyncio.gather(*[upload_file(file) for file in files])
        
        asyncio.run(async_run(uploaded_files))
        
        if len(st.session_state["uploaded_file_ids"]) == len(uploaded_files):
            upload_msg_layer.success("Files uploaded successfully!")

# chat section
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# generate AI message
if prompt := st.chat_input():
    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    with st.spinner('답변 생성중'):
        response = requests.post(f"{BACKEND_URL}/invoke",
                                    json={
                                        "openai_api_key": openai_api_key,
                                        "prompt": prompt,
                                        "files": st.session_state.uploaded_file_ids
                                    },
                                    headers={
                                        'accept': 'application/json',
                                        'Content-Type': 'application/json'
                                        }
                                    )
        msg = response.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant").write(msg)
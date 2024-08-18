import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import json
import streamlit as st
import requests
import asyncio
import aiohttp
import urllib.parse

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
                async with session.post(url, data=data, json=json, timeout=aiohttp.ClientTimeout(total=6000)) as response:
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
                    # convert txt -> dict
                    print(f"upload_file result: {file_info}")
                    index_params = json.loads(file_info)
                    index_params['extract_images'] = False
                    print(f"indexing params: {index_params}")
                    # file indexing
                    result = await async_post(session, url=f"{BACKEND_URL}/indexing", filename=file.name, json=index_params)
                    
                    if result:
                        st.session_state["uploaded_file_ids"].append(json.loads(result))
        
        # 비동기 파일 업로드 실행
        async def async_run(files):
            await asyncio.gather(*[upload_file(file) for file in files])
        
        asyncio.run(async_run(uploaded_files))
        
        if len(st.session_state.uploaded_file_ids) >= len(uploaded_files):
            upload_msg_layer.success("Files uploaded successfully!")

# chat section
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# generate AI message
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    with st.spinner('답변 생성중'):
        print(st.session_state.messages)
        print(st.session_state.uploaded_file_ids)
        searchResult = requests.post(f"{BACKEND_URL}/search",
                                    json={
                                        "file_infos": st.session_state.uploaded_file_ids,
                                        "messages": st.session_state.messages
                                        }
                                    )
        content = json.loads(searchResult.content.decode('utf-8'))
        tooltips = []
        for citation in content['citations']:
            print(citation)
            if citation['document']:
                title = urllib.parse.unquote(citation['source'])
                for i in range(len(citation['document'])):
                    tooltips.append({
                        'title': title,
                        'content': citation['document'][i],
                        'page': citation['metadata'][i]['page']
                    })

        response = requests.post(f"{BACKEND_URL}/invoke",
                                    json={
                                    "input": {
                                        "file_infos": st.session_state.uploaded_file_ids,
                                        "messages": st.session_state.messages
                                    },
                                    "config": {},
                                    "kwargs": {}
                                    },
                                    headers={
                                        'Content-Type': 'application/json'
                                        }
                                    )
        if response.ok:
            content = json.loads(response.content.decode('utf-8'))
            print(f"generate result: {content}")
            msg = content['output']
            st.session_state.messages.append({"role": "assistant", "content": msg})
            st.chat_message("assistant").write(msg)

            if len(tooltips)> 0:
                with st.container():
                    for idx, tooltip in enumerate(tooltips, start=1):
                        if tooltip['page'] != None:
                            st.text(f"[{idx}] {tooltip['title']} ({tooltip['page']}p)", help = tooltip['content'])
                        else:
                            st.text(f"[{idx}] {tooltip['title']}", help = tooltip['content'])
        else:
            st.error(response)
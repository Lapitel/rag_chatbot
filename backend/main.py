import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import json
import logging
from typing import List
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    status
)
import uuid
import uvicorn
from langchain_core.pydantic_v1 import BaseModel, Field
from langserve import add_routes, CustomUserType
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.schema.runnable import RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories.file import FileChatMessageHistory
from langchain_core.messages import BaseMessage

from config import (
    GLOBAL_LOG_LEVEL,
    UPLOAD_DIR,
    CONFIG_DATA
)

from apps import index
from apps import search
from apps.utils import get_last_user_message

# log setting
log = logging.getLogger(__name__)
log.setLevel(GLOBAL_LOG_LEVEL)

app = FastAPI(
    title="RAG Chatbot API Server",
    version="1.0",
    description="RAG Chatbot API Server",
)

@app.post("/file")
def upload_file(file: UploadFile = File(...)):
    try:
        log.info(f"upload_file(): {file.filename}")
        # metadata
        unsanitized_filename = file.filename
        filename = os.path.basename(unsanitized_filename)
        file_ext = filename.split(".")[-1].lower()
        id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, id)
        contents = file.file.read()
        
        # Check if the file is a PDF
        # python magic은 운영체제에 따라 설치 및 사용방법이 달라 사용 보류

        # mimeType = magic.from_buffer(contents, mime=True)
        # if mimeType != "application/pdf":
        if file_ext != "pdf":
            log.exception(f"{file.content_type} content_type not allowed.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed."
            )
        
        with open(file_path, "wb") as f:
            f.write(contents)
            f.close()

        return {'file_id': id, 'name': filename}
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e
        )

class IndexParams(BaseModel):
    file_id: str
    name: str
    extract_images: bool

@app.post("/indexing")
def indexing(index_params: IndexParams):
    try:
        log.info(f"indexing(): {index_params}")
        # get loader
        loader = index.get_loader(index_params.file_id, extract_images=index_params.extract_images)
        data = loader.load()
        log.info(f"indexing() len(data): {len(data)}")
        # split chunk
        docs = index.get_split_docs(data, index_params.name)
        log.info(f"indexing() len(docs): {len(docs)}")
        # store vector DB
        index.store_docs_in_vector_db(docs=docs, collection_name=index_params.file_id)
        
        return {"file_id": index_params.file_id, "name": index_params.name, "docs_count": len(docs)}
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

llm = ChatOpenAI()
# generation parameters
class GenerateRequest(CustomUserType):
    file_infos: list[dict] = None
    messages: list[dict]

def generate(request: GenerateRequest):
    context = ""
    citations = []
    # search
    if request.file_infos:
        contexts, citations = search.get_rag_context(
            file_infos=request.file_infos,
            messages=request.messages,
            k=CONFIG_DATA['rag']['top_k'],
            r=CONFIG_DATA['rag']['relevance_threshold'],
            llm
        )
        context = "/n".join(contexts).strip()

    return {"contexts": context, "chat_history": request.messages[:-1], "question": get_last_user_message(request.messages), "citations": citations}

prompt = ChatPromptTemplate.from_messages([
    ("system","""Use the following context as your learned knowledge, inside <context></context> XML tags.
                <context>
                    {context}
                </context>

                When answer to user:
                - If you don't know, just say that you don't know.
                - If you don't know when you are not sure, ask for clarification.
                Avoid mentioning that you obtained the information from the context.
                And answer according to the language of the user's question.

                Given the context information, answer the query.
                Query: """),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])

add_routes(
    app,
    RunnableLambda(generate).with_types(input_type=GenerateRequest),
    prompt | ChatOpenAI()
)

# @app.get("/generate_session_id")
# def generate_session_id():
#     return {'session_id': str(uuid.uuid4().hex)}

# LOCK_FILE_PATH = os.path.join(config['api_path'], config['file_db_path'], 'indexing.lock')
# @app.get("/total_indexing")
# def indexing(progress: Optional[int] = None):
#     if progress == 1:
#         if os.path.exists(LOCK_FILE_PATH):
#             return {'msg': 'Indexing in progress.'}
#         else:
#             return {'msg': 'Indexing not in progress.'}
        
#     if os.path.exists(LOCK_FILE_PATH):
#         return {'msg': 'Indexing in progress.'}
    
#     t = threading.Thread(target=async_indexing.async_indexing)
#     t.start()

#     return {'msg': 'Indexing has started.'}

# @app.post("/get_retriever_result")
# def get_retriever_result(input: FileProcessingRequest):
#     return process_file(input)['docs']

if __name__ == "__main__":
    uvicorn.run('main:app', host="0.0.0.0", port=8080)
    # uvicorn.run('main:app', host="0.0.0.0", port=8080, reload=True)
import os
import logging
from config import (
    GLOBAL_LOG_LEVEL,
    UPLOAD_DIR,
    CONFIG_DATA
)

if CONFIG_DATA['openai_api_key']:
    os.environ["OPENAI_API_KEY"] = CONFIG_DATA['openai_api_key']
else:
    import getpass
    os.environ["OPENAI_API_KEY"] = getpass.getpass("OpenAI API Key:")

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    status
)
import uuid
import uvicorn
from langchain_core.pydantic_v1 import BaseModel
from langserve import add_routes, CustomUserType
from langchain.schema.runnable import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from apps import index
from apps import search
from apps.utils import get_last_user_message, search_file_db, insert_file_db, update_index_complete

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
        file_size = file.size
        
        # 파일관리 DB 검색 - 중복방지
        result = search_file_db(filename=filename, file_size=file_size)
        if result:
            return {'file_id': result['file_id'], 'name': result['name']}
            
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
        insert_file_db(id, filename, file_size)
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
        # 파일관리 DB 검색 - 중복작업방지
        result = search_file_db(file_id=index_params.file_id)
        if result and result['docs_count'] > 0:
            return {'file_id': result['file_id'], 'name': result['name'], "docs_count": result['docs_count']}
        
        # get loader
        loader = index.get_loader(index_params.file_id, extract_images=index_params.extract_images)
        data = loader.load()
        # log.info(f"indexing() len(data): {len(data)}")
        # split chunk
        docs = index.get_split_docs(data, index_params.name)
        # log.info(f"indexing() len(docs): {len(docs)}")
        # store vector DB
        index.store_docs_in_vector_db(docs=docs, collection_name=index_params.file_id)
        
        update_index_complete(index_params.file_id, len(docs))
        return {"file_id": index_params.file_id, "name": index_params.name, "docs_count": len(docs)}
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

llm = ChatOpenAI(model="gpt-3.5-turbo")
# generation parameters
class SearchRequest(CustomUserType):
    file_infos: list[dict] = None
    messages: list[dict]

@app.post("/search")
def searching(request: SearchRequest):
    context = ""
    citations = []
    # search
    if request.file_infos:
        contexts, citations = search.get_rag_context(
            file_infos=request.file_infos,
            messages=request.messages,
            k=CONFIG_DATA['rag']['top_k'],
            r=CONFIG_DATA['rag']['relevance_threshold'],
            llm=llm
        )
        context = "/n".join(contexts).strip()

    return {"context": context, "question": get_last_user_message(request.messages), "citations": citations}

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
    ("human", "{question}")
])

add_routes(
    app,
    {'context': RunnablePassthrough(), 'question': RunnablePassthrough()} | prompt | llm | StrOutputParser()
)

if __name__ == "__main__":
    # stream_hander = logging.StreamHandler()
    # log.addHandler(stream_hander)
    # request = GenerateRequest(file_infos=[{'file_id': 'fa3dab54-1bfa-4dc7-a1c4-4b56d6610c21', 'name':'2407.01219v1.pdf'}], messages=[{'role': 'assistant', 'content': 'How can I help you?'}, {'role': 'user', 'content': '논문에서 제시된 vector DB중 어떤것이 가장 좋아?'}])
    # print(generate(request))
    uvicorn.run('main:app', host="0.0.0.0", port=8080)
    # uvicorn.run('main:app', host="0.0.0.0", port=8080, reload=True)
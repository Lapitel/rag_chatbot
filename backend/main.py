import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import logging
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    status
)
import uuid
import uvicorn
from pydantic import BaseModel
from langserve import add_routes, CustomUserType

from config import (
    GLOBAL_LOG_LEVEL,
    UPLOAD_DIR,
    CONFIG_DATA
)

from apps import index

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

class FileInfo(BaseModel):
    file_id: str
    name: str

@app.post("/indexing")
def upload_file(file_info: FileInfo):
    log.info(file_info)
    # get loader
    loader = index.get_loader(file_info.file_id)
    data = loader.load()
    # split chunk
    docs = index.get_split_docs(data)
    # embedding
    if len(docs) > 0:
        texts = [doc.page_content for doc in docs]
        metadatas = [{**doc.metadata, **(file_info if file_info else {})} for doc in docs]
    # store vector DB
    
    return file_info

# generation parameters
class GenerateRequest(CustomUserType):
    collection_names: list[str] = None
    prompt: str

# def process_file(request: GenerateRequest):
#     if request.files:
#         for file in files:
#             file.
#         content = base64.decodebytes(request.file.encode("utf-8"))
#         # # 파일의 해시값 계산
#         # file_hash = hashlib.sha256(content)
#         # hex_dig = file_hash.hexdigest()
#         # # 해시값 압축 (byte)
#         # compress_hash = base64.b64encode(bytes.fromhex(hex_dig))
#         # # 해시값에 슬러시(/)가 존재할 경우 에러발생. 언더바(_)로 치환
#         # filename = compress_hash.decode('utf-8').replace("/","_")
#         filePath = os.path.join(config["api_path"], 'upload_file_temp', request.file_name)
#         #파일 저장
#         with open(filePath, "wb") as file:
#             file.write(content)

#         filenames.append(filePath)
#     if request.uploaded_filenames:
#         #디렉토리여부 확인
#         for filename in request.uploaded_filenames:
#             filePath = os.path.join(config["api_path"], config["upload_file_path"], filename)
#             if os.path.isdir(filePath):
#                 for root, dirs, files in os.walk(filePath):
#                 # 하위 파일들을 filenames 리스트에 추가
#                     for file in files:
#                         filenames.append(os.path.join(root, file))
#             elif os.path.isfile(filename):
#                 filenames.append(filePath)
#         #filenames.extend(request.uploaded_filenames)
    
#     #검색
#     if filenames:
#         docs = retriever.getRetriverDocuments(filenames, request.question, request.test_args)
#         if docs: 
#             context = "\n\n".join([x.page_content for x in docs])

#     return {"context": context, "question": request.question, "docs": docs if docs else []}

# chain_with_history = RunnableWithMessageHistory(
#     chain.getChain(llm_name=config['use_llm']),
#     lambda session_id: CustomHistory(session_id, url=f"redis://{config['redis_url']}/0", logfile_path=os.path.join(config["api_path"],"logs")),
#     input_messages_key="question",
#     history_messages_key="history"
# )

# add_routes(
#     app,
#     RunnableLambda(process_file).with_types(input_type=FileProcessingRequest) | chain_with_history,
# #    enabled_endpoints=("invoke", "stream", "stream_log", "playground")
# )

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
    uvicorn.run('main:app', host="0.0.0.0", port=8080, reload=True)
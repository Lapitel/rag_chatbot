import logging
from config import (
    GLOBAL_LOG_LEVEL
)
from fastapi import FastAPI
from langserve import add_routes, CustomUserType

# 로그 설정
log = logging.getLogger(__name__)
log.setLevel(GLOBAL_LOG_LEVEL)

app = FastAPI(
    title="RAG Chatbot API Server",
    version="1.0",
    description="RAG Chatbot API Server",
)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=config['api_port'])
    parser.add_argument("--llm", type=str, default=config['use_llm'])
    args = parser.parse_args()

    config.set_value('use_llm', args.llm)
    config.set_value('api_port', args.port)

# 매개변수 정의
class FileProcessingRequest(CustomUserType):
    uploaded_filenames: list[str] = None
    file: str = Field(default="", extra={"widget": {"type": "base64file"}})
    file_name: str = ""
    question: str
    test_args: dict = {}

def process_file(request: FileProcessingRequest):    
    filenames = []
    docs = []
    context = ""
    if request.file:
        content = base64.decodebytes(request.file.encode("utf-8"))
        # # 파일의 해시값 계산
        # file_hash = hashlib.sha256(content)
        # hex_dig = file_hash.hexdigest()
        # # 해시값 압축 (byte)
        # compress_hash = base64.b64encode(bytes.fromhex(hex_dig))
        # # 해시값에 슬러시(/)가 존재할 경우 에러발생. 언더바(_)로 치환
        # filename = compress_hash.decode('utf-8').replace("/","_")
        filePath = os.path.join(config["api_path"], 'upload_file_temp', request.file_name)
        #파일 저장
        with open(filePath, "wb") as file:
            file.write(content)

        filenames.append(filePath)
    if request.uploaded_filenames:
        #디렉토리여부 확인
        for filename in request.uploaded_filenames:
            filePath = os.path.join(config["api_path"], config["upload_file_path"], filename)
            if os.path.isdir(filePath):
                for root, dirs, files in os.walk(filePath):
                # 하위 파일들을 filenames 리스트에 추가
                    for file in files:
                        filenames.append(os.path.join(root, file))
            elif os.path.isfile(filename):
                filenames.append(filePath)
        #filenames.extend(request.uploaded_filenames)
    
    #검색
    if filenames:
        docs = retriever.getRetriverDocuments(filenames, request.question, request.test_args)
        if docs: 
            context = "\n\n".join([x.page_content for x in docs])

    return {"context": context, "question": request.question, "docs": docs if docs else []}

chain_with_history = RunnableWithMessageHistory(
    chain.getChain(llm_name=config['use_llm']),
    lambda session_id: CustomHistory(session_id, url=f"redis://{config['redis_url']}/0", logfile_path=os.path.join(config["api_path"],"logs")),
    input_messages_key="question",
    history_messages_key="history"
)

add_routes(
    app,
    RunnableLambda(process_file).with_types(input_type=FileProcessingRequest) | chain_with_history,
#    enabled_endpoints=("invoke", "stream", "stream_log", "playground")
)

@app.get("/generate_session_id")
def generate_session_id():
    return {'session_id': str(uuid.uuid4().hex)}

LOCK_FILE_PATH = os.path.join(config['api_path'], config['file_db_path'], 'indexing.lock')
@app.get("/total_indexing")
def indexing(progress: Optional[int] = None):
    if progress == 1:
        if os.path.exists(LOCK_FILE_PATH):
            return {'msg': 'Indexing in progress.'}
        else:
            return {'msg': 'Indexing not in progress.'}
        
    if os.path.exists(LOCK_FILE_PATH):
        return {'msg': 'Indexing in progress.'}
    
    t = threading.Thread(target=async_indexing.async_indexing)
    t.start()

    return {'msg': 'Indexing has started.'}

@app.post("/get_retriever_result")
def get_retriever_result(input: FileProcessingRequest):
    return process_file(input)['docs']

if __name__ == "__main__":
    # 최초실행시 indexing lock파일 제거
    if os.path.exists(LOCK_FILE_PATH):
        os.remove(LOCK_FILE_PATH)
    
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "[%(asctime)s %(levelname)s] %(message)s"
    log_config["formatters"]["access"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
    
    uvicorn.run(app, host="0.0.0.0", port=config['api_port'], log_config=log_config)
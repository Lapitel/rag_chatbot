# 프로젝트 개요
- 제목: PDF 문서 기반 RAG 챗봇
- 소개: LangServe(Langchain)기반 RAG기술을 탑재한 챗봇 애플리케이션입니다. RAG를 원하는 문서를 업로드하여, 문서기반 질의&답변을 할 수 있습니다.

## 데모


## 프로젝트 특징
 - 모듈화: 파일업로드, 벡터화 색인, 검색 등을 별도로 모듈화하여, 확장에 용이하도록 설계
 - 동시성 해결: Langserve를 활용하여 요청에 대한 동시성 보장

## 주요 기능
- 멀티턴 에이전트: 사용자 대화 히스토리 + 최종 질의를 합성하여, 문맥 최적화 후 RAG검색에 사용
- 하이브리드 검색: bm25(tf/idf 기반) + vector 검색 지원
- RAG문서 압축 & 리랭킹: RAG 결과를 압축 & 리랭킹하여 제공함으로써 답변 품질 향상
- 모델 토큰 제한 해결: 멀티턴 에이전트의 압축, RAG문서의 압축을 통해 해결
- RAG 검색 청크 preview: RAG사용시 검색된 청크를 preview할 수 있는 기능

### 전제 조건
- NVIDIA GPU 필요 (임베딩 모델 로컬 동작을 위해)
- CUDA 설치 필요
- Python 3.11 필요
- OPENAI API Key 필요

### 설치 방법
1. 저장소를 클론합니다.
  ```bash
  git clone https://github.com/Lapitel/rag_chatbot.git
  ```
2. 프로젝트 디렉토리로 이동합니다.
  ```bash
  cd rag_chatbot
  ```
3. 필요한 의존성을 설치합니다.
  ```bash
  pip install -r requirements.txt
  ```

### 시작하기
1. openai_api_key 입력
- backend/data/config.json 내 openai_api_key 입력(미입력시 openai 접근시마다 API key 요청함)
2. backend
  ```bash
  cd backend
  python main.py
  ```
3. frontend
  ```bash
  streamlit run ./frontend/chatbot.py
  ```
4. chatbot URL 접속
- http://{{ip}}:8501/

### 한계점
- PDF -> Vector DB 저장과정이 비동기로 실행되나, 작업에 있어 시간이 많이 소요됨. 비동기처리 완성도가 부족하여 웹화면 로딩걸림.
- Frontend -> Backend로 대화 생성시, 업로드가 다시 요청됨 (단, 파일이름과 사이즈로 중복작업은 제거)
- 멀티모달 기능: GPU 자원이 부족하여, 테스트 및 코딩 불가.
- 모델 토큰 제한 해결: 멀티턴 에이전트의 압축, RAG문서의 압축을 통해 1차원적인 해결방법만 적용.
- 미완의 Test코드: 레퍼런스 코드 분석에 시간을 많이 들여, Test코드 작성이 미흡함 

### 앞으로의 개선 방향
- 멀티모달 기능 개발
- 모델 토큰 제한 해결: Map-Reduce 혹은 LangGraph를 통한 근본적인 해결방안 적용
- 비동기 처리: 별도 Frontend 개발을 통해 비동기 부분 개선
- PDF -> Vector DB 저장과정 속도 개선: RAG용 Vector DB를 일배치 등 스케쥴러를 통해 Vector DB 구축 

### 참고사항
- 임베딩 속도가 느려, vector_db를 함께 업로드 함. (파일이름과 사이즈가 같은 파일 업로드시 임베딩 과정 생략)
- 최초 색인, 검색시 임베딩모델 및 리랭킹용 모델을 다운로드 받기 때문에, 생성속도가 느림.
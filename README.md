# 프로젝트 개요
- 제목: PDF 문서 기반 RAG 챗봇
- 소개: PDF문서를 기반으로 RAG를 활용한 챗봇 프로젝트로, 사용자 질의에 대해 문서기반 답변을 제공하는 어플리케이션입니다.

## 데모
[여기에 프로젝트의 작동 모습을 보여주는 스크린샷 또는 GIF를 추가할 수 있습니다.]

## 주요 기능
- 하이브리드 검색:
- RAG문서 압축 & 리랭킹 :
- 멀티턴 에이전트: [기능 3에 대한 설명]
- 토큰 제한 맵리듀스 지원:
- 멀티모달 지원: 

### 전제 조건
- GPU 필요 (임베딩 모델 로컬 동작을 위해)
- CUDA 설치 필요
- Python 3.11 필요
- Streamlit 설치 필요
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
- backend
  ```bash
  cd backend
  python main.py
  ```
- frontend
  ```bash
  streamlit run .\frontend\chatbot.py
  ```

### 한계점
- PDF -> Vector DB 저장과정이 비동기로 실행되나, 작업에 있어 시간이 많이 소요됨
- Frontend -> Backend로 대화 생성시, 업로드가 다시 요청됨 (단, 파일이름과 사이즈로 중복작업은 제거)

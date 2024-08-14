import logging
from pathlib import Path
import json
import os
import sys

# 로그 설정
GLOBAL_LOG_LEVEL = "INFO"
logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL, force=True)

# 백엔드 소스 경로
BACKEND_DIR = Path(__file__).parent
# 프로젝트 경로
BASE_DIR = BACKEND_DIR.parent
# 데이터 저장 경로
DATA_DIR = Path(os.path.join(BACKEND_DIR, "data")).resolve()
# 프론트엔드 소스 경로
FRONTEND_DIR = Path(os.path.join(BASE_DIR, "frontend")).resolve()

# 업로드 파일 경로
UPLOAD_DIR = Path(os.path.join(DATA_DIR, "uploads")).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

try:
    CONFIG_DATA = json.loads((DATA_DIR / "config.json").read_text())
except:
    CONFIG_DATA = {}
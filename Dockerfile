# 1. 베이스 이미지 (Python 3.12 slim)
FROM python:3.12-slim

# 2. 환경 변수 기본 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. 워킹 디렉토리
WORKDIR /app

# 4. 시스템 의존성
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 5. 의존성 파일만 먼저 복사 (레이어 캐싱)
COPY requirements.txt /app/

# 6. 파이썬 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 7. 앱 코드 복사
COPY . /app

# 8. 포트
EXPOSE 8080

# 9. Uvicorn으로 FastAPI 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
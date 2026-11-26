FROM python:3.11-slim

WORKDIR /app

# 只装运行必需依赖，跳过体积大且经常装不上的 sherpa-onnx
RUN pip install --no-cache-dir \
    fastapi "uvicorn[standard]" python-multipart pydantic \
    python-dotenv edge-tts PyJWT bcrypt numpy langchain-core

COPY . .

RUN mkdir -p /data && \
    python -c "import sys; sys.path.insert(0,'/app/app/backend')" 

ENV COACH_DB_PATH=/data/coach.sqlite
ENV PYTHONUNBUFFERED=1

WORKDIR /app/app/backend
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn httpx websockets
COPY server.py index.html ./
EXPOSE 3000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000", "--ws-ping-interval", "20", "--ws-ping-timeout", "20"]

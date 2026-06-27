FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir "fastapi>=0.110.0" "uvicorn[standard]>=0.30.0" "httpx>=0.27.0" "websockets>=12.0"
COPY server.py index.html ./
EXPOSE 3000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]

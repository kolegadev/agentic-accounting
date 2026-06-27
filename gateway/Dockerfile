FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Expose the MCP Gateway port
EXPOSE 3112

# Run the server
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "3112", "--log-level", "info"]

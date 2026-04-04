FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Build context is the project root — copy requirements first for layer caching
COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ .

# Copy core RAG agent logic into the image (NOT a volume mount)
# This makes the image self-contained and deployable via docker pull alone
COPY src/ /app/src/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
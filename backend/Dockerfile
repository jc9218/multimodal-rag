# Latest Stable / Maintenance LTS Python
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (build-essential, curl, OCR engine for scanned PDFs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Create storage directories
RUN mkdir -p /app/storage/uploads /app/storage/images

ENV PYTHONUNBUFFERED=1
ENV MALLOC_ARENA_MAX=2
ENV PORT=8000

EXPOSE ${PORT}

# Run with uvicorn listening to $PORT with a single worker to preserve memory in 512MB containers
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
